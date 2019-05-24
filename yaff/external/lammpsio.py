# -*- coding: utf-8 -*-
# YAFF is yet another force-field code.
# Copyright (C) 2011 Toon Verstraelen <Toon.Verstraelen@UGent.be>,
# Louis Vanduyfhuys <Louis.Vanduyfhuys@UGent.be>, Center for Molecular Modeling
# (CMM), Ghent University, Ghent, Belgium; all rights reserved unless otherwise
# stated.
#
# This file is part of YAFF.
#
# YAFF is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# YAFF is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>
#
# --
'''lammpsio

    Reading/writing of LAMMPS output/input files
'''

import numpy as np
import os

from yaff.log import log
from yaff.pes import PairPotEI, ForcePartPair
from yaff.sampling.utils import cell_lower

from molmod.units import angstrom

__all__ = ['write_lammps_system_data','write_lammps_table','get_lammps_ffatypes',
           'read_lammps_table']

def write_lammps_system_data(system, ff=None, fn='lammps.data', triclinic=True):
    '''
        Write information about a Yaff system to a LAMMPS data file
        Following information is written: cell vectors, atom type ids
        and topology (as defined by the bonds)

        **Arguments**
            system
                Yaff system

            fn
                Filename to write the LAMMPS data to

            triclinic
                Boolean, specify whether a triclinic cell will be used during
                the simulation. If the cell is orthogonal, set it to False
                as LAMMPS should run slightly faster.
                Default: True
    '''
    if system.cell.nvec != 3:
        raise ValueError('The system must be 3D periodic for Lammps calculations.')
    if system.ffatypes is None:
        raise ValueError('Atom types need to be defined.')
    if system.bonds is None:
        raise ValueError('Bonds need to be defined')
    if system.charges is None:
        if log.do_warning:
            log.warn("System has no charges, writing zero charges to LAMMPS file")
        charges = np.zeros((system.natom,))
    else:
        charges = system.charges
    if ff is None:
        ffatypes, ffatype_ids = system.ffatypes, system.ffatype_ids
    else:
        ffatypes, ffatype_ids = get_lammps_ffatypes(ff)
    fdat = open(fn,'w')
    fdat.write("Generated by Yaff\n\n%20d atoms\n%20d bonds\n%20d angles \n%20d dihedrals\n%20d impropers\n\n" % (system.natom, system.nbond, 0, 0, 0))
    fdat.write("%20d atom types\n%20d bond types\n%20d angle types\n%20d dihedral types\n%20d improper types\n\n" % (np.amax(ffatype_ids) + 1, 1,0,0,0) )
    rvecs, R = cell_lower(system.cell.rvecs)
    pos = np.einsum('ij,kj', system.pos, R)
    fdat.write("%30.24f %30.24f xlo xhi\n%30.24f %30.24f ylo yhi\n%30.24f %30.24f zlo zhi\n" % (0.0,rvecs[0,0],0.0,rvecs[1,1],0.0,rvecs[2,2]) )
    if triclinic:
        fdat.write("%30.24f %30.24f %30.24f xy xz yz\n" % (rvecs[1,0],rvecs[2,0],rvecs[2,1]) )
    fdat.write("Atoms\n\n")
    for i in range(system.natom):
        fdat.write("%5d %3d %3d %30.24f %30.24f %30.24f %30.24f\n" % (i+1,1,ffatype_ids[i]+1, charges[i], pos[i,0], pos[i,1], pos[i,2]) )
    fdat.write("\nBonds\n\n")
    for i in range(system.nbond):
        fdat.write("%5d %3d %5d %5d\n" % (i+1,1,system.bonds[i,0]+1, system.bonds[i,1]+1))
    fdat.close()

def write_lammps_table(ff, fn='lammps.table', rmin=0.50*angstrom, nrows=2500):
    '''
       Write tables containing noncovalent interactions for LAMMPS.
       For every pair of ffatypes, a separate table is generated.
       Because electrostatic interactions require a specific treatment, point-
       charge electrostatics are NOT included in the tables.

       When distributed charge distributions (e.g. Gaussian) are used, this
       complicates matters. LAMMPS will still only treat point-charge
       electrostatics using a dedicated method (e.g. Ewald or PPPM), so the
       table has to contain the difference between the distributed charges and
       the point charge electrostatic interactions. This also means that every
       ffatype need a unique charge distribution, i.e. all atoms of the same
       atom type need to have the same charge and Gaussian radius.

       All pair potentials contributing to the table need to have the same
       scalings for near-neighbor interactions; this is however independent
       of the generation of the table and is dealt with elsewhere

       **Arguments:**

       ff
            Yaff ForceField instance

       **Optional arguments:**

       fn
            Filename where tables will be stored

    '''
    # Find out if we are dealing with electrostatics from distributed charges
    corrections = []
    for part in ff.parts:
        if part.name=='pair_ei':
            if np.any(part.pair_pot.radii!=0.0):
                # Create a ForcePart with electrostatics from distributed
                # charges, completely in real space.
                pair_pot_dist = PairPotEI(part.pair_pot.charges, 0.0,
                     part.pair_pot.rcut, tr=part.pair_pot.get_truncation(),
                     dielectric=part.pair_pot.dielectric, radii=part.pair_pot.radii)
                fp_dist = ForcePartPair(ff.system,ff.nlist,part.scalings,pair_pot_dist)
                corrections.append( (fp_dist,1.0) )
                # Create a ForcePart with electrostatics from point
                # charges, completely in real space.
                pair_pot_point = PairPotEI(part.pair_pot.charges, 0.0,
                     part.pair_pot.rcut, tr=part.pair_pot.get_truncation(),
                     dielectric=part.pair_pot.dielectric)
                fp_point = ForcePartPair(ff.system,ff.nlist,part.scalings,pair_pot_point)
                corrections.append( (fp_point,-1.0) )
    # Find the largest cut-off
    rmax = 0.0
    for part in ff.parts:
        if part.name.startswith('pair_'):
            if part.name=='pair_ei' and len(corrections)==0: continue
            rmax = np.amax([rmax,part.pair_pot.rcut])
    # Get LAMMPS ffatypes
    ffatypes, ffatype_ids = get_lammps_ffatypes(ff)
    # Select atom pairs for each pair of atom types
    ffa_pairs = []
    for i in range(len(ffatypes)):
        index0 = np.where(ffatype_ids==i)[0][0]
        for j in range(i,len(ffatypes)):
            index1 = -1
            candidates = np.where(ffatype_ids==j)[0]
            for cand in candidates:
                if cand==index0 or cand in ff.system.neighs1[index0] or\
                    cand in ff.system.neighs2[index0] or cand in ff.system.neighs3[index0] or\
                    cand in ff.system.neighs4[index0]: continue
                else:
                    index1 = cand
                    break
            if index1==-1:
                log("ERROR constructing LAMMPS tables: there is no pair of atom types %s-%s which are not near neighbors"%(ffatypes[i],ffatypes[j]))
                log("Consider using a supercell to fix this problem")
                raise ValueError
            ffa_pairs.append([index0,index1])
    if log.do_medium:
        with log.section('LAMMPS'):
            log("Generating LAMMPS table with covalent interactions")
            log.hline()
            log("rmin = %s | rmax = %s" % (log.length(rmin),log.length(rmax)))
    # We only consider one neighbor interaction
    ff.compute()
    ff.nlist.nneigh = 1
    # Construct array of evenly spaced values
    distances = np.linspace(rmin, rmax, nrows)
    ftab = open(fn,'w')
    ftab.write("# LAMMPS tabulated potential generated by Yaff\n")
    ftab.write("# All quantities in atomic units\n")
    ftab.write("# The names of the tables refer to the ffatype_ids that have to be used in the Yaff system\n")
    ftab.write("#%4s %13s %21s %21s\n" % ("i","d","V","F"))
    # Loop over all atom pairs
    for index0, index1 in ffa_pairs:
        energies = []
        for d in distances:
            gposnn = np.zeros(ff.system.pos.shape, float)
            ff.nlist.neighs[0] = (index0, index1, d, 0.0, 0.0, d, 0, 0, 0)
            energy = 0.0
            for part in ff.parts:
                if not part.name.startswith('pair'): continue
                if part.name=='pair_ei': continue
                energy += part.compute(gpos=gposnn)
            for part, sign in corrections:
                gposcorr = np.zeros(ff.system.pos.shape, float)
                energy += sign*part.compute(gpos=gposcorr)
                gposnn[:] += sign*gposcorr
            row = [d, energy, gposnn[index0,2]]
            energies.append( row )
        energies = np.asarray(energies)
        ffai = ffatypes[ffatype_ids[index0]]
        ffaj = ffatypes[ffatype_ids[index1]]
        if np.all(energies[:,1]==0.0):
            log.warn("Noncovalent energies between atoms %d (%s) and %d (%s) are zero"\
                    % (index0,ffai,index1,ffaj))
        if np.all(energies[:,2]==0.0):
            log.warn("Noncovalent forces between atoms %d (%s) and %d (%s) are zero"\
                    % (index0,ffai,index1,ffaj))
        if ffai>ffaj:
            name = '%s---%s' % (str(ffai),str(ffaj))
        else:
            name = '%s---%s' % (str(ffaj),str(ffai))
        ftab.write("%s\nN %d R %f %f\n\n" % (name, nrows, rmin, rmax))
        for irow, row in enumerate(energies):
            ftab.write("%05d %+13.8f %+21.12f %+21.12f\n" % (irow+1, row[0], row[1], row[2]))
        if log.do_medium:
            log("%s done"%name)
#        if make_plots:
#            if not os.path.isdir(os.path.join(workdir,'lammps_table_plots')): os.mkdir(os.path.join(workdir,'lammps_table_plots'))
#            pt.clf()
#            #pt.subplot(2,1,1)
#            pt.plot(energies[:,0]/angstrom,energies[:,1]/kjmol)
#            pt.yscale('symlog',linthreshy=1.0)
#            #pt.gca().set_xticks(np.arange(1.5,9.0,1.5))
#            #pt.gca().set_yticks(np.arange(-50,75,12.5))
#            #pt.xlim([1.5,7.5])
#            #pt.ylim([-50.0,50.0])
#            pt.xlabel('d [$\AA$]')
#            pt.ylabel('E [kJ/mol]')
#            #pt.subplot(2,1,2)
#            #pt.plot(energies[:,0]/angstrom,energies[:,2])
#            pt.savefig(os.path.join(workdir,'lammps_table_plots','%s.png'%name))


def get_lammps_ffatypes(ff):
    '''
    Fine grain the atomtypes, so that each atomtype has a unique charge and
    Gaussian radius. This is only necessary when electrostatics from charge
    distributions are used, so otherwise the original atomtypes are returned.
    '''
    newffas = None
    for part in ff.parts:
        if part.name=='pair_ei':
            if np.any(part.pair_pot.radii!=0.0):
                newffas = [ff.system.get_ffatype(iatom) for iatom in range(ff.system.natom)]
                # Loop over all atomtypes
                for iffa, ffa in enumerate(ff.system.ffatypes):
                    ei_combs = []
                    for iatom in np.where(ff.system.ffatype_ids==iffa)[0]:
                        comb = (part.pair_pot.charges[iatom],part.pair_pot.radii[iatom])
                        if not comb in ei_combs: ei_combs.append(comb)
                        newffas[iatom] = "%s_%05d"%(newffas[iatom],ei_combs.index(comb))
                ffatypes = list(set(newffas))
                ffatype_ids = np.zeros(ff.system.natom, int)
                for iatom in range(ff.system.natom):
                    ffatype_ids[iatom] = ffatypes.index(newffas[iatom])
                return ffatypes, ffatype_ids
    return ff.system.ffatypes, ff.system.ffatype_ids


def read_lammps_table(fn):
    tables = []
    with open(fn,'r') as f:
        while True:
            line = f.readline()
            if not line: break
            if line.startswith('#'): continue
            ffas = line[:-1]
            w = f.readline().split()
            N, rmin, rmax = int(w[1]), float(w[3]), float(w[4])
            data = np.zeros((N,3))
            f.readline()
            for i in range(N):
                data[i] = [float(w) for w in f.readline().split()[1:]]
            tables.append((ffas,[N,rmin,rmax],data))
    return tables
