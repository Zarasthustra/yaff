# YAFF is yet another force-field code
# Copyright (C) 2008 - 2012 Toon Verstraelen <Toon.Verstraelen@UGent.be>, Center
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


import shutil, tempfile

from yaff import *


def test_consistency():
    pf1 = Parameters.from_file('input/parameters_bks.txt')
    dirname = tempfile.mkdtemp('yaff', 'test_consistency_parameters')
    try:
        pf1.write_to_file('%s/parameters_bks.txt' % dirname)
        pf2 = Parameters.from_file('%s/parameters_bks.txt' % dirname)
        assert len(pf1.sections) == len(pf2.sections)
        for prefix1, section1 in pf1.sections.iteritems():
            section2 = pf2[prefix1]
            assert section1.prefix == section2.prefix
            assert len(section1.definitions) == len(section2.definitions)
            for suffix1, lines1 in section1.definitions.iteritems():
                lines2 = section2.definitions[suffix1]
                assert len(lines1) == len(lines2)
                for (counter1, data1), (counter2, data2) in zip(lines1, lines2):
                    assert data1 == data2
    finally:
        shutil.rmtree(dirname)


def test_from_file():
    pf = Parameters.from_file('input/parameters_bks.txt')
    assert pf['EXPREP']['CPARS'][0][1] == '       O        O  1.3887730000e+03  2.7600000000e+00'
    assert pf['DAMPDISP']['UNIT'][2][0] == 10
    assert pf['FIXQ']['SCALE'][-1][1] == '3 1.0'