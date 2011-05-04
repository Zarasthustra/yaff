# YAFF is yet another force-field code
# Copyright (C) 2008 - 2011 Toon Verstraelen <Toon.Verstraelen@UGent.be>, Center
# for Molecular Modeling (CMM), Ghent University, Ghent, Belgium; all rights
# reserved unless otherwise stated.
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


import numpy as np

from molmod import kcalmol, angstrom, rad, deg, femtosecond, boltzmann
from molmod.periodic import periodic
from molmod.io import XYZWriter

from yaff import *

from common import get_system_water32, check_gpos_ff, check_vtens_ff

def get_ff_water32(do_valence=False, do_lj=False, do_eireal=False, do_eireci=False):
    system = get_system_water32()
    rcut = 9*angstrom
    alpha = 4.5/rcut
    scalings = Scalings(system.topology)
    parts = []
    if do_valence:
        # Valence part
        vpart = ValencePart(system)
        for i, j in system.topology.bonds:
            vpart.add_term(Harmonic(450.0*kcalmol/angstrom**2, 0.9572*angstrom, Bond(i, j)))
        for i1 in xrange(system.natom):
            for i0 in system.topology.neighs1[i1]:
                for i2 in system.topology.neighs1[i1]:
                    if i0 > i2:
                        vpart.add_term(Harmonic(55.000*kcalmol/rad**2, 104.52*deg, BendAngle(i0, i1, i2)))
        parts.append(vpart)
    if do_lj or do_eireal:
        # Neighbor lists, scalings
        nlists = NeighborLists(system)
    else:
        nlists = None
    if do_lj:
        # Lennard-Jones part
        rminhalf_table = {1: 0.2245*angstrom, 8: 1.7682*angstrom}
        epsilon_table = {1: -0.0460*kcalmol, 8: -0.1521*kcalmol}
        sigmas = np.zeros(96, float)
        epsilons = np.zeros(96, float)
        for i in xrange(system.natom):
            sigmas[i] = rminhalf_table[system.numbers[i]]*(2.0)**(5.0/6.0)
            epsilons[i] = epsilon_table[system.numbers[i]]
        pair_pot_lj = PairPotLJ(sigmas, epsilons, rcut, True)
        pair_part_lj = PairPart(system, nlists, scalings, pair_pot_lj)
        parts.append(pair_part_lj)
    # charges
    q0 = 0.417
    charges = -2*q0 + (system.numbers == 1)*3*q0
    assert abs(charges.sum()) < 1e-8
    if do_eireal:
        # Real-space electrostatics
        pair_pot_ei = PairPotEI(charges, alpha, rcut)
        pair_part_ei = PairPart(system, nlists, scalings, pair_pot_ei)
        parts.append(pair_part_ei)
    if do_eireci:
        # Reciprocal-space electrostatics
        ewald_reci_part = EwaldReciprocalPart(system, charges, alpha, gcut=alpha/0.75)
        parts.append(ewald_reci_part)
        # Ewald corrections
        ewald_corr_part = EwaldCorrectionPart(system, charges, alpha, scalings)
        parts.append(ewald_corr_part)
    return ForceField(system, parts, nlists)


def test_gpos_water32_full():
    ff = get_ff_water32(True, True, True, True)
    check_gpos_ff(ff, 1e-10)


def test_vtens_water32_full():
    ff = get_ff_water32(True, True, True, True)
    check_vtens_ff(ff, 1e-10)


def test_md_water32_full():
    dump = False
    ff = get_ff_water32(True, True, True, True)
    pos = ff.system.pos.copy()
    grad = np.zeros(pos.shape)
    h = 1.0*femtosecond
    mass = np.array([periodic[n].mass for n in ff.system.numbers]).reshape((-1,1))
    # init
    ff.update_pos(pos)
    epot = ff.compute(grad)
    temp = 300
    vel = np.random.normal(0, 1, pos.shape)*np.sqrt((2*boltzmann*temp)/mass)
    velh = vel + (-0.5*h)*grad/mass
    # prop
    cqs = []
    if dump:
        xyz_writer = XYZWriter('traj.xyz', ff.system.ffatypes)
    for i in xrange(100):
        pos += velh*h
        ff.update_pos(pos)
        grad[:] = 0.0
        epot = ff.compute(grad)
        if dump:
            xyz_writer.dump('i = %i  energy = %.10f' % (i, epot), pos)
        tmp = (-0.5*h)*grad/mass
        vel = velh + tmp
        ekin = 0.5*(mass*vel*vel).sum()
        cqs.append(ekin + epot)
        velh = vel + tmp
    cqs = np.array(cqs)
    assert cqs.std() < 5e-3
