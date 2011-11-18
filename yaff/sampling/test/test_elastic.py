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

from yaff import *
from yaff.sampling.test.common import get_ff_water32, get_ff_water, get_ff_bks


def test_elastic_water32():
    ff = get_ff_water32()
    elastic = estimate_elastic(ff)
    assert elastic.shape == (6, 6)


def test_elastic_water():
    ff = get_ff_water()
    elastic = estimate_elastic(ff)
    assert elastic.shape == (6, 6)


def test_bulk_modulus_water32():
    ff = get_ff_water32()
    bulk_modulus = estimate_bulk_modulus(ff)
    assert bulk_modulus > 0


def test_bulk_modulus_bks():
    ff = get_ff_bks()
    bulk_modulus = estimate_bulk_modulus(ff)
    assert bulk_modulus > 0
