# -*- coding: utf-8 -*-
# YAFF is yet another force-field code
# Copyright (C) 2011 - 2012 Toon Verstraelen <Toon.Verstraelen@UGent.be>,
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
#--



import numpy as np

from molmod import boltzmann, femtosecond

from yaff.log import log
from yaff.sampling.utils import get_random_vel, remove_com_vel
from yaff.sampling.verlet import VerletHook


__all__ = [
    'AndersenThermostat', 'NHCThermostat', 'LangevinThermostat',
]


class AndersenThermostat(VerletHook):
    def __init__(self, temp, start=0, step=1, select=None, annealing=1.0):
        """
           This is an implementation of the Andersen thermostat. The method
           is described in:

                Andersen, H. C. J. Chem. Phys. 1980, 72, 2384-2393.

           **Arguments:**

           temp
                The average temperature of the NVT ensemble

           **Optional arguments:**

           start
                The first iteration at which this hook is called

           step
                The number of iterations between two subsequent calls to this
                hook.

           select
                An array of atom indexes to indicate which atoms controlled by
                the thermostat.

           annealing
                After every call to this hook, the temperature is multiplied
                with this annealing factor. This effectively cools down the
                system.
        """
        self.temp = temp
        self.select = select
        self.annealing = annealing
        VerletHook.__init__(self, start, step)

    def init(self, iterative):
        pass

    def pre(self, iterative):
        pass

    def post(self, iterative):
        # Needed to correct the conserved quantity
        ekin_before = iterative._compute_ekin()
        # Change the (selected) velocities
        if self.select is None:
            iterative.vel[:] = get_random_vel(self.temp, False, iterative.masses)
        else:
            iterative.vel[self.select] = get_random_vel(self.temp, False, iterative.masses, self.select)
        # Update the kinetic energy and the reference for the conserved quantity
        ekin_after = iterative._compute_ekin()
        self.econs_correction += ekin_before - ekin_after
        # Optional annealing
        self.temp *= self.annealing


class NHChain(object):
    # TODO: allow for manual override of the ndof argument
    def __init__(self, length, timestep, temp, ndof, timecon=100*femtosecond):
        # parameters
        self.length = length
        self.timestep = timestep
        self.temp = temp
        self.timecon = timecon
        self.set_ndof(ndof)

        # allocate degrees of freedom
        self.pos = np.zeros(length)
        self.vel = np.zeros(length) # TODO: sensible random initial velocities?

    def set_ndof(self, ndof):
        # set the masses according to the time constant
        self.ndof = ndof
        angfreq = 2*np.pi/self.timecon
        self.masses = np.ones(self.length)*(boltzmann*self.temp/angfreq**2)
        self.masses[0] *= ndof

    def __call__(self, ekin, vel):
        def do_bead(k, ekin):
            # Compute g
            if k == 0:
                # coupling with atoms
                # L = 3N because of equidistant time steps.
                g = 2*ekin - self.ndof*self.temp*boltzmann
            else:
                # coupling between beads
                g = self.masses[k-1]*self.vel[k-1]**2 - self.temp*boltzmann
            g /= self.masses[k]

            # Lioville operators on relevant part of the chain
            if k == self.length-1:
                # iL G_k h/4
                self.vel[k] += g*self.timestep/4
            else:
                # iL vxi_{k-1} h/8
                self.vel[k] *= np.exp(-self.vel[k+1]*self.timestep/8)
                # iL G_k h/4
                self.vel[k] += g*self.timestep/4
                # iL vxi_{k-1} h/8
                #print self.vel[k], self.vel[k+1], self.timestep
                self.vel[k] *= np.exp(-self.vel[k+1]*self.timestep/8)

        # Loop over chain in reverse order
        for k in xrange(self.length-1, -1, -1):
            do_bead(k, ekin)

        # iL xi (all) h/2
        self.pos += self.vel*self.timestep/2

        # iL Cv (all) h/2
        factor = np.exp(-self.vel[0]*self.timestep/2)
        vel *= factor
        ekin *= factor**2

        # Loop over chain in forward order
        for k in xrange(0, self.length):
            do_bead(k, ekin)

        return ekin

    def get_econs_correction(self):
        kt = boltzmann*self.temp
        return 0.5*(self.vel**2*self.masses).sum() + kt*(self.ndof*self.pos[0] + self.pos[1:].sum())


class NHCThermostat(VerletHook):
    def __init__(self, temp, start=0, timecon=100*femtosecond, chainlength=3):
        """
           This hook implements the Nose-Hoover-Chain thermostat. The equations
           are derived in:

                Martyna, G. J.; Klein, M. L.; Tuckerman, M. J. Chem. Phys. 1992,
                97, 2635-2643.

           The implementation (used here) of a symplectic integrator of the
           Nose-Hoover-Chain thermostat is discussed in:

                Martyna, G. J.;  Tuckerman, M. E.;  Tobias, D. J.;  Klein,
                M. L. Mol. Phys. 1996, 87, 1117-1157.

           **Arguments:**

           temp
                The temperature of thermostat.

           **Optional arguments:**

           start
                The step at which the thermostat becomes active.

           timecon
                The time constant of the Nose-Hoover thermostat.

           chainlength
                The number of beads in the Nose-Hoover chain.
        """
        self.temp = temp
        # At this point, the timestep and the number of degrees of freedom are
        # not known yet.
        self.chain = NHChain(chainlength, 0.0, temp, 0, timecon)
        VerletHook.__init__(self, start, 1)

    def init(self, iterative):
        remove_com_vel(iterative.vel, iterative.masses)
        self.chain.timestep = iterative.timestep
        self.chain.set_ndof(iterative.pos.size)

    def pre(self, iterative):
        iterative.ekin = self.chain(iterative.ekin, iterative.vel)

    def post(self, iterative):
        ekin = iterative._compute_ekin()
        iterative.ekin = self.chain(ekin, iterative.vel)
        self.econs_correction = self.chain.get_econs_correction()


class LangevinThermostat(VerletHook):
    def __init__(self, temp, start=0, timecon=100*femtosecond):
        """
           This is an implementation of the Langevin thermostat. The algorithm
           is described in:

                Bussi, G.; Parrinello, M. Phys. Rev. E 2007, 75, 056707

           **Arguments:**

           temp
                The temperature of thermostat.

           **Optional arguments:**

           start
                The step at which the thermostat becomes active.

           timecon
                The time constant of the Nose-Hoover thermostat.
        """
        self.temp = temp
        self.timecon = timecon
        VerletHook.__init__(self, start, 1)

    def init(self, iterative):
        pass

    def pre(self, iterative):
        self.thermo(iterative)

    def post(self, iterative):
        self.thermo(iterative)

    def thermo(self, iterative):
        c1 = np.exp(-iterative.timestep/self.timecon/2)
        c2 = np.sqrt((1.0-c1**2)*self.temp*boltzmann/iterative.masses).reshape(-1,1)
        ekin_before = iterative._compute_ekin()
        iterative.vel[:] = c1*iterative.vel + c2*np.random.normal(0, 1, iterative.vel.shape)
        ekin_after = iterative._compute_ekin()
        self.econs_correction += ekin_before - ekin_after
