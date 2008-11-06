# plot.py, abstract plotting classes
# Reinier Heeres <reinier@heeres.eu>
# Pieter de Groot <pieterdegroot@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gobject
import logging
import os
import time
import types

import qt
import namedlist

from misc import get_arg_type, get_dict_keys
from data import Data

class _PlotList(namedlist.NamedList):
    def __init__(self, time_name=False):
        namedlist.NamedList.__init__(self, base_name='plot')

class Plot(gobject.GObject):
    '''
    Base class / interface for plot implementations.

    Implementing _do_update will make sure the plot is updated when new data
    is available (only when the global qt auto_update flag is set and the
    plot was last updated longer than mintime (sec) ago.
    '''

    _plot_list = _PlotList()

    def __init__(self, *args, **kwargs):
        '''
        Create a plot object.

        args input:
            data objects (Data)
            filenames (string)

        kwargs input:
            name (string), default will be 'plot<n>'
            maxpoints (int), maximum number of points to show, default 10000
            maxtraces (int), maximum number of traces to show, default 5
            mintime (int, seconds), default 1
            autoupdate (bool), default None, which means listen to global
        '''

        gobject.GObject.__init__(self)

        maxpoints = kwargs.get('maxpoints', 10000)
        maxtraces = kwargs.get('maxtraces', 5)
        mintime = kwargs.get('mintime', 1)
        autoupdate = kwargs.get('autoupdate', None)
        name = kwargs.get('name', '')
        self._name = Plot._plot_list.new_item_name(self, name)

        self._config = qt.config
        self._data = []

        self._maxpoints = maxpoints
        self._maxtraces = maxtraces
        self._mintime = mintime
        self._autoupdate = autoupdate

        self._last_update = 0

        for arg in args:
            if isinstance(arg, Data):
                data_args = get_dict_keys(kwargs, ('coorddim', 'coorddims', 'valdim'))
                self.add_data(arg, **data_args)
            elif type(arg) is types.StringType and os.path.isfile(arg):
                data = Data(arg)
                self.add_data(data)

        Plot._plot_list.add(name, self)

    def add_data(self, data, **kwargs):
        '''Add a Data class with options to the plot list.'''

        kwargs['data'] = data
        self._data.append(kwargs)

        data.connect('new-data-point', self._new_data_point_cb)
        data.connect('new-data-block', self._new_data_block_cb)

    def set_title(self, val):
        '''Set the title of the plot window. Override in implementation.'''
        pass

    def add_legend(self, val):
        '''Add a legend to the plot window. Override in implementation.'''
        pass

    def update(self, force=True, **kwargs):
        '''
        Update the plot.

        Input:
            force (bool): if True force an update, else check whether we
                would like to autoupdate and whether the last update is longer
                than 'mintime' ago.
        '''

        dt = time.time() - self._last_update

        if not force and self._autoupdate is not None and not self._autoupdate:
            return

        cfgau = self._config.get('auto-update', True)
        if force or (cfgau and dt > self._mintime):
            self._last_update = time.time()
            self._do_update(**kwargs)

    def _new_data_point_cb(self, sender):
        try:
            self.update(force=False)
        except Exception, e:
            logging.warning('Failed to update plot %s: %s', self._name, str(e))

    def _new_data_block_cb(self, sender):
        self.update(force=False)

    def set_maxpoints(self, val):
        self._maxpoints = val

    @staticmethod
    def get_named_list():
        return Plot._plot_list

    @staticmethod
    def get(name):
        return Plot._plot_list[name]

class Plot2D(Plot):
    '''
    Abstract base class for a 2D plot.
    Real implementations should at least implement:
        - set_xlabel(self, label)
        - set_ylabel(self, label)
    '''

    def __init__(self, *args, **kwargs):
        Plot.__init__(self, *args, **kwargs)

    def add_data(self, data, coorddim=None, valdim=None, **kwargs):
        '''
        Add data to 2D plot.

        Input:
            data (Data):
                Data object
            coorddim (int):
                Which coordinate column to use (0 by default)
            valdim (int):
                Which value column to use for plotting (0 by default)
        '''

        if coorddim is None:
            if data.get_ncoordinates() > 1:
                logging.info('Data object has multiple coordinates, using the first one')
            coorddims = (0,)
        else:
            coorddims = (coorddim,)

        if valdim is None:
            if data.get_nvalues() > 1:
                logging.info('Data object has multiple values, using the first one')
            valdim = data.get_ncoordinates()
            if valdim < 1:
                valdim = 1

        kwargs['coorddims'] = coorddims
        kwargs['valdim'] = valdim
        Plot.add_data(self, data, **kwargs)

    def set_labels(self, left='', bottom='', right='', top=''):
        for datadict in self._data:
            data = datadict['data']
            if 'right' in datadict and right == '':
                right = data.format_label(datadict['coorddims'][0])
            elif left == '':
                left = data.format_label(datadict['coorddims'][0])

            if 'top' in datadict and top == '':
                top = data.format_label(datadict['valdim'])
            elif bottom == '':
                bottom = data.format_label(datadict['valdim'])

        if left != '':
            self.set_xlabel(left)
        if right != '':
            self.set_xlabel(right, right=True)
        if bottom != '':
            self.set_ylabel(bottom)
        if top != '':
            self.set_ylabel(top, top=True)

    def plotxy(self, vecx, vecy):
        pass

class Plot3D(Plot):
    '''
    Abstract base class for a 3D plot.
    Real implementations should at least implement:
        - set_xlabel(self, label)
        - set_ylabel(self, label)
        - set_zlabel(self, label)
    '''

    def __init__(self, *args, **kwargs):
        Plot.__init__(self, *args, **kwargs)

    def add_data(self, data, coorddims=None, valdim=None):
        '''
        Add data to 3D plot.

        Input:
            data (Data):
                Data object
            coorddim (tuple(int)):
                Which coordinate columns to use ((0, 1) by default)
            valdim (int):
                Which value column to use for plotting (0 by default)
        '''

        if coorddims is None:
            if data.get_ncoordinates() > 2:
                logging.info('Data object has multiple coordinates, using the first two')
            coorddims = (0, 1)

        if valdim is None:
            if data.get_nvalues() > 1:
                logging.info('Data object has multiple values, using the first one')
            valdim = data.get_ncoordinates()
            if valdim < 2:
                valdim = 2

        Plot.add_data(self, data, coorddims=coorddims, valdim=valdim)

    def set_labels(self, x='', y='', z=''):
        '''
        Set labels in the plot. Use x, y and z if specified, else let the data
        object create the proper format for each dimensions
        '''

        for datadict in self._data:
            data = datadict['data']
            if x == '':
                x = data.format_label(datadict['coorddims'][0])
            if y == '':
                y = data.format_label(datadict['coorddims'][1])
            if z == '':
                z = data.format_label(datadict['valdim'])

        if x != '':
            self.set_xlabel(x)
        if y != '':
            self.set_ylabel(y)
        if z != '':
            self.set_zlabel(z)

    def plotxyz(self, vecx, vecy, vecz):
        pass

