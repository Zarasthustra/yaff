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


cimport pair_pot
cimport cell

cdef extern from "ewald.h":
    double compute_ewald_reci(double *pos, long natom, long nlow, long nhigh, double *charges,
                              cell.cell_type *unitcell, double alpha,
                              long *gmax, double gcut, double dielectric,
                              double *gpos, double *work, double* vtens)

    double compute_ewald_reci_dd(double *pos, long natom, long nlow, long nhigh, double *charges, double *dipoles,
                              cell.cell_type *unitcell, double alpha,
                              long *gmax, double gcut, double *gpos,
                              double *work, double* vtens)

    double compute_ewald_corr(double *pos, double *charges,
                              cell.cell_type *unitcell, double alpha,
                              pair_pot.scaling_row_type *stab, long stab_size,
                              double dielectric, double *gpos, double *vtens,
                              long natom, long nlow, long nhigh)

    double compute_ewald_corr_dd(double *pos, double *charges, double *dipoles,
                              cell.cell_type *unitcell, double alpha,
                              pair_pot.scaling_row_type *stab,
                              long stab_size, double *gpos, double *vtens,
                              long natom, long nlow, long nhigh)

    void compute_ewald_prefactors(cell.cell_type* cell, double alpha, long *gmax, double
                              gcut, double *prefactors)

    void compute_ewald_structurefactors(double *pos, long natom, double *charges,
                              cell.cell_type* cell, double alpha, long *gmax, double
                              gcut, double *cosfacs, double* sinfacs)

    double compute_ewald_deltae(double *deltacosfacs,
                                double *cosfacs,
                                double *deltasinfacs,
                                double *sinfacs,
                                double *prefactors, long nk)
