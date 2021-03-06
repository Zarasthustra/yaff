#!/usr/bin/env python
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

import subprocess

subprocess.check_call(["python", "mksystem.py"], cwd='init')
subprocess.check_call(["python", "simulation.py"], cwd='opt')
subprocess.check_call(["python", "analysis.py"], cwd='opt')
subprocess.check_call(["python", "simulation.py", "300", "310"], cwd='nvt')
subprocess.check_call(["python", "analysis.py", "300", "310", "10"], cwd='nvt')
