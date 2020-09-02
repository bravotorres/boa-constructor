#----------------------------------------------------------------------------
# Name:         Debugger.py
# Purpose:      wxPython debugger, started as a port of IDLE's debugger
#               written by Guido van Rossum
#
# Authors:      Riaan Booysen, Shane Hathaway
#
# Created:      2000/01/11
# RCS-ID:       $Id$
# Copyright:    (c) Riaan Booysen, Shane Hathaway
# Copyright:    (c) 2000 - 2007 : Riaan Booysen, Shane Hathaway
# Licence:      GPL
#----------------------------------------------------------------------------

# XXX I must still try to see if it's not possible the change code while
# XXX debugging, reload sometimes works
# XXX Going to source code on an error

import string, sys, os
from repr import Repr
import traceback, linecache, imp, pprint, time

from wxPython.wx import *

import Preferences, Utils
from Preferences import pyPath, IS, flatTools
from Breakpoint import bplist
from DebugClient import EVT_DEBUGGER_OK, EVT_DEBUGGER_EXC, EVT_DEBUGGER_STOPPED

# When an output window surpasses these limits, it will be trimmed.
TEXTCTRL_MAXLEN = 30000
TEXTCTRL_GOODLEN = 20000

wxID_STACKVIEW = NewId()
class StackViewCtrl(wxListCtrl):
    def __init__(self, parent, flist, debugger):
        wxListCtrl.__init__(self, parent, wxID_STACKVIEW,
                            style = wxLC_REPORT | wxLC_SINGLE_SEL )
        self.InsertColumn(0, 'Frame', wxLIST_FORMAT_LEFT, 150)
        self.InsertColumn(1, 'Line', wxLIST_FORMAT_LEFT, 35)
        self.InsertColumn(2, 'Code', wxLIST_FORMAT_LEFT, 300)
        EVT_LIST_ITEM_SELECTED(self, wxID_STACKVIEW,
                               self.OnStackItemSelected)
        EVT_LIST_ITEM_DESELECTED(self, wxID_STACKVIEW,
                                 self.OnStackItemDeselected)
        EVT_LEFT_DCLICK(self, self.OnGotoSource)

import wx

    def load_stack(self, stack, index=None):
        self.stack = stack
        data = []

        pos = 0
        count = self.GetItemCount()
        for entry in stack:
            lineno = entry['lineno']
            modname = entry['modname']
            filename = entry['client_filename']
            funcname = entry['funcname']
            sourceline = linecache.getline(filename, lineno)
            sourceline = string.strip(sourceline)
            if funcname in ("?", "", None):
                #item = "%s, line %d: %s" % (modname, lineno, sourceline)
                attrib = modname
            else:
                #item = "%s.%s(), line %d: %s" % (modname, funcname,
                #                                 lineno, sourceline)
                # XXX methods will be shown as "module.function"
                # when maybe they ought to be shown as "module.class.method".
                attrib = modname + '.' + funcname
            #if pos == index:
            #    item = "> " + item
            if pos >= count:
                # Insert.
                self.InsertStringItem(pos, attrib)
                count = count + 1
            else:
                # Update.
                self.SetStringItem(pos, 0, attrib, -1)
            self.SetStringItem(pos, 1, `lineno`, -1)
            self.SetStringItem(pos, 2, sourceline, -1)
            pos = pos + 1

        while pos < count:
            self.DeleteItem(count - 1)
            count = count - 1
        self.selection = -1

    def OnStackItemSelected(self, event):
        self.selection = event.m_itemIndex

        stacklen = len(self.stack)
        if 0 <= self.selection < stacklen:
            self.debugger.invalidatePanes()
            self.debugger.updateSelectedPane()

wxID_PAGECHANGED = wx.NewId()
wxID_TOPPAGECHANGED = wx.NewId()
class DebuggerFrame(wx.Frame, Utils.FrameRestorerMixin):
    debug_client = None
    _destroyed = 0
    _closing = 0

    def selectCurrentEntry(self):
        newsel = self.GetItemCount() - 1
        if newsel != self.selection:
            if self.selection >= 0:
                item = self.GetItem(self.selection)
                item.m_state = item.m_state & ~wxLIST_STATE_SELECTED
                self.SetItem(item)
            if newsel >= 0:
                item = self.GetItem(newsel)
                item.m_state = item.m_state | wxLIST_STATE_SELECTED
                self.SetItem(item)
            self.selection = newsel
        if newsel >= 0:
            self.EnsureVisible(newsel)

    def OnGotoSource(self, event):
        if self.selection != -1:
            entry = self.stack[self.selection]
            lineno = entry['lineno']
            modname = entry['modname']
            filename = entry['client_filename']
            if not filename:
                return

            editor = self.debugger.editor
            editor.SetFocus()
            editor.openOrGotoModule(filename)
            model = editor.getActiveModulePage().model
            model.views['Source'].focus()
            model.views['Source'].SetFocus()
            model.views['Source'].selectLine(lineno - 1)


[wxID_BREAKVIEW, wxID_BREAKSOURCE, wxID_BREAKEDIT, wxID_BREAKDELETE,
  wxID_BREAKENABLED, wxID_BREAKREFRESH] = map(lambda x: NewId(), range(6))

        self.toolbar = wx.ToolBar(self, -1,
              style=wx.TB_HORIZONTAL | wx.NO_BORDER|flatTools)
        self.SetToolBar(self.toolbar)

        self.brkImgLst = wxImageList(16, 16)
        self.brkImgLst.Add(IS.load('Images/Debug/Breakpoint-red.png'))
        self.brkImgLst.Add(IS.load('Images/Debug/Breakpoint-yellow.png'))
        self.brkImgLst.Add(IS.load('Images/Debug/Breakpoint-gray.png'))
        self.brkImgLst.Add(IS.load('Images/Debug/Breakpoint-blue.png'))

##        EVT_LIST_ITEM_SELECTED(self, wxID_BREAKVIEW,
##                               self.OnBreakpointSelected)
##        EVT_LIST_ITEM_DESELECTED(self, wxID_BREAKVIEW,
##                                 self.OnBreakpointDeselected)
        EVT_LEFT_DCLICK(self, self.OnGotoSource)

        self.SetAcceleratorTable(wx.AcceleratorTable( [
          (keyDefs['Debug'][0], keyDefs['Debug'][1], self.runId),
          (keyDefs['DebugStep'][0], keyDefs['DebugStep'][1], self.stepId),
          (keyDefs['DebugOver'][0], keyDefs['DebugOver'][1], self.overId),
          (keyDefs['DebugOut'][0], keyDefs['DebugOut'][1], self.outId) ] ))

        self.toolbar.Realize()

        self.menu.Append(wxID_BREAKSOURCE, 'Goto source')
        self.menu.Append(wxID_BREAKREFRESH, 'Refresh')
        self.menu.Append(-1, '-')
        self.menu.Append(wxID_BREAKEDIT, 'Edit')
        self.menu.Append(wxID_BREAKDELETE, 'Delete')
        self.menu.Append(-1, '-')
        self.menu.Append(wxID_BREAKENABLED, 'Enabled', checkable = true)
        self.menu.Check(wxID_BREAKENABLED, true)
        EVT_MENU(self, wxID_BREAKSOURCE, self.OnGotoSource)
        EVT_MENU(self, wxID_BREAKREFRESH, self.OnRefresh)
        EVT_MENU(self, wxID_BREAKEDIT, self.OnEdit)
        EVT_MENU(self, wxID_BREAKDELETE, self.OnDelete)
        EVT_MENU(self, wxID_BREAKENABLED, self.OnToggleEnabled)
        self.pos = None

        self.splitter = wx.SplitterWindow(self, -1,
               style=wx.SP_NOBORDER|Preferences.splitterStyle)

        self.rightsel = -1
        self.debugger = debugger
        self.bps = []
        self.stats = {}

    def destroy(self):
        self.menu.Destroy()
        self.brkImgLst = None

    def refreshList(self):
        self.rightsel = -1
        self.DeleteAllItems()
        bps = bplist.getBreakpointList()
        # Sort by filename and lineno.
        bps.sort(lambda a, b:
                 cmp((a['filename'], a['lineno']),
                     (b['filename'], b['lineno'])))
        self.bps = bps
        for p in range(len(bps)):
            bp = bps[p]
            imgIdx = 0
            if not bp['enabled']:
                imgIdx = 2
            elif bp['temporary']: imgIdx = 3

            self.InsertImageStringItem(
                p, os.path.basename(bp['filename']), imgIdx)
            self.SetStringItem(p, 1, str(bp['lineno']))
            if bp['enabled']: self.SetStringItem(p, 3, '*')

            hits = ''
            ignore = ''
            if self.stats:
                for item in self.stats:
                    if (bp['filename'] == item['client_filename'] and
                        bp['lineno'] == item['lineno']):
                        hits = str(item['hits'])
                        ignore = str(item['ignore'])
                        break
            self.SetStringItem(p, 2, ignore)
            self.SetStringItem(p, 3, hits)
            self.SetStringItem(p, 4, bp['cond'] or '')

    def addBreakpoint(self, filename, lineno):
        self.refreshList()

##    def OnBreakpointSelected(self, event):
##        self.selection = event.m_itemIndex

##    def OnBreakpointDeselected(self, event):
##        self.selection = -1

    def OnGotoSource(self, event):
        sel = self.rightsel
        if sel != -1:
            bp = self.bps[sel]
            filename = bp['filename']
            if not filename:
                return

            editor = self.debugger.editor
            editor.SetFocus()
            editor.openOrGotoModule(filename)
            model = editor.getActiveModulePage().model
            model.views['Source'].focus()
            model.views['Source'].SetFocus()
            model.views['Source'].selectLine(bp['lineno'] - 1)

        self.lastStepView = None
        self.lastStepLineno = -1

    def OnDelete(self, event):
        sel = self.rightsel
        if sel != -1:
            bp = self.bps[sel]
            filename = bp['filename']
            bplist.deleteBreakpoints(filename, bp['lineno'])

            server_fn = self.debugger.clientFNToServerFN(filename)
            self.debugger.invokeInDebugger(
                'clearBreakpoints', (server_fn, bp['lineno']))

            # TODO: Unmark the breakpoint in the editor.
            self.refreshList()

        self.setServerClientPaths([])

    def OnToggleEnabled(self, event):
        sel = self.rightsel
        if sel != -1:
            bp = self.bps[sel]
            filename = bp['filename']
            lineno = bp['lineno']
            enabled = not bp['enabled']
            bplist.enableBreakpoints(filename, lineno, enabled)
            self.debugger.invokeInDebugger(
                'enableBreakpoints', (filename, lineno, enabled))
            self.refreshList()

    def OnRightDown(self, event):
        self.pos = event.GetPosition()

    def OnRightClick(self, event):
        if not self.pos:
            return
        sel = self.HitTest(self.pos)[0]
        if sel != -1:
            self.rightsel = sel
            bp = self.bps[sel]
            self.menu.Check(wxID_BREAKENABLED, bp['enabled'])
            self.PopupMenu(self.menu, self.pos)

        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnToolOver)
        self.Bind(wx.EVT_CLOSE, self.OnCloseWindow)

# XXX Expose classes' dicts as indented items
wxID_NSVIEW = NewId()
class NamespaceViewCtrl(wxListCtrl):
    def __init__(self, parent, add_watch, is_local, name):  # , dict=None):
        wxListCtrl.__init__(self, parent, wxID_NSVIEW,
          style = wxLC_REPORT | wxLC_SINGLE_SEL )
        self.InsertColumn(0, 'Attribute', wxLIST_FORMAT_LEFT, 125)
        self.InsertColumn(1, 'Value', wxLIST_FORMAT_LEFT, 200)

        EVT_LIST_ITEM_SELECTED(self, -1, self.OnItemSelect)
        EVT_LIST_ITEM_DESELECTED(self, -1, self.OnItemDeselect)
        self.selected = -1

        EVT_RIGHT_DOWN(self, self.OnRightDown)
        EVT_COMMAND_RIGHT_CLICK(self, -1, self.OnRightClick)
        EVT_RIGHT_UP(self, self.OnRightClick)

        self.is_local = is_local

        self.menu = wxMenu()

        idAs = NewId()
        idA = NewId()
        self.menu.Append(idAs, 'Add as watch')
        self.menu.Append(idA, 'Add a %s watch' % name)
        EVT_MENU(self, idAs, self.OnAddAsWatch)
        EVT_MENU(self, idA, self.OnAddAWatch)
        self.pos = None

        self.repr = Repr()
        self.repr.maxstring = 60
        self.repr.maxother = 60
        self.names = []

        self.add_watch = add_watch

        # self.load_dict(dict)

    def destroy(self):
        self.menu.Destroy()

    dict = -1

    def showLoading(self):
        self.DeleteAllItems()
        self.InsertStringItem(0, '...')

    def load_dict(self, dict, force=0):
        #if dict == self.dict and not force:
        #    return

        self.breakpts.destroy()
        self.watches.destroy()
        self.locs.destroy()
        self.globs.destroy()
        self.sb.stateCols = None
        if self.stream_timer is not None:
            self.stream_timer.Stop()
            self.stream_timer = None

        if not dict:
            pass
        else:
            self.names = dict.keys()
            self.names.sort()
            row = 0
            for name in self.names:
                svalue = dict[name]
                #svalue = self.repr.repr(value) # repr(value)

    _sashes_inited = 0
    def initSashes(self):
        if not self._sashes_inited:
            s = self.GetSize()
            if s.x /float(s.y) > 1:
                mode = wx.SPLIT_HORIZONTAL
            else:
                mode = wx.SPLIT_VERTICAL
            self.splitter.SetSplitMode(mode)
            self.OnToggleSplitOrient()
            self._sashes_inited = 1

    def add_watch(self, name, local):
        self.watches.add_watch(name, local)
        self.nbBottom.SetSelection(0)
        self.invalidatePanes()
        self.updateSelectedPane()

    def OnPageChange(self, event):
        sel = event.GetSelection()
        if sel >= 0:
            self.updateSelectedPane(sel)
        event.Skip()

    def OnAddAsWatch(self, event):
        if self.rightsel != -1:
            name = self.names[self.rightsel]
            self.add_watch(name, self.is_local)

    def updateSelectedPane(self, pageno=-1, do_request=1, force=0):
        if pageno < 0:
            pageno = self.nbBottom.GetSelection()
        if not self.updated_panes[pageno] or force:
            frameno = self.stackView.getSelection()
            if pageno == 0:
                self.watches.showLoading()
                if do_request:
                    self.requestWatches(frameno)
            else:
                if pageno==1: self.locs.showLoading()
                else: self.globs.showLoading()
                if do_request:
                    self.requestDict((pageno==1), frameno)

    def requestWatches(self, frameno):
        ws = self.watches.watches
        exprs = []
        for name, local in ws:
            exprs.append({'name':name, 'local':local})
        if exprs:
            self.invokeInDebugger(
                'evaluateWatches', (exprs, frameno), 'receiveWatches')
        else:
            # No exprs, so no request is necessary.
            self.watches.load_dict(None)
            self.updated_panes[0] = 1

    def receiveWatches(self, status):
        frameno = status['frameno']
        if frameno == self.stackView.getSelection():
            self.updated_panes[0] = 1
            self.watches.load_dict(status['watches'])
        else:
            # Re-request.
            self.updateSelectedPane()

    def OnRightDown(self, event):
        self.pos = event.GetPosition()

    def OnRightClick(self, event):
        if not self.pos:
            return
        sel = self.HitTest(self.pos)[0]
        if sel != -1:
            self.rightsel = sel
            self.PopupMenu(self.menu, self.pos)

    def requestWatchSubobjects(self, name, local, pos):
        self.invokeInDebugger(
            'getWatchSubobjects', (name, self.stackView.getSelection()),
            'receiveWatchSubobjects', (name, local, pos))

    def receiveWatchSubobjects(self, subnames, name, local, pos):
        for subname in subnames:
            self.watches.add_watch('%s.%s' % (name, subname), local, pos)
            pos = pos + 1
        self.nbBottom.SetSelection(0)
        self.invalidatePanes()
        self.updateSelectedPane()

    def __init__(self, parent, images, debugger):
        wxListCtrl.__init__(self, parent, wxID_WATCHVIEW,
          style = wxLC_REPORT | wxLC_SINGLE_SEL )
        self.InsertColumn(0, 'Attribute', wxLIST_FORMAT_LEFT, 125)
        self.InsertColumn(1, 'Value', wxLIST_FORMAT_LEFT, 200)

    def receiveVarValue(self, val):
        if val:
            self.editor.setStatus(val)

    def getVarValue(self, name):
        if not name.strip():
            return None
        self._hasReceivedVal = 0
        self._receivedVal = None
        self.invokeInDebugger(
            'pprintVarValue', (name, self.stackView.getSelection()),
            'receiveVarValue2')
        # XXX I'm not comfortable with this...
        try:
            while not self._hasReceivedVal:
                wx.Yield()
            return self._receivedVal
        finally:
            del self._hasReceivedVal
            del self._receivedVal

    def receiveVarValue2(self, val):
        self._receivedVal = val
        self._hasReceivedVal = 1

##        EVT_LIST_ITEM_SELECTED(self, -1, self.OnItemSelect)
##        EVT_LIST_ITEM_DESELECTED(self, -1, self.OnItemDeselect)
        self.rightsel = -1

#---------------------------------------------------------------------------

        self.menu = wxMenu()

        id = NewId()
        self.menu.Append(id, 'Delete')
        EVT_MENU(self, id, self.OnDelete)
        id = NewId()
        self.menu.Append(id, 'Expand')
        EVT_MENU(self, id, self.OnExpand)
        id = NewId()
        self.menu.Append(id, 'Delete All')
        EVT_MENU(self, id, self.OnDeleteAll)
        self.pos = None

    def destroy(self):
        self.menu.Destroy()

    dict = -1

    def add_watch(self, name, local, pos=-1):
        if name:
            if pos < 0 or pos >= len(self.watches):
                self.watches.append((name, local))
            else:
                self.watches.insert(pos, (name, local))
        else:
            dlg = wxTextEntryDialog(
                self, 'Enter name:', 'Add a watch:', '')
            try:
                if dlg.ShowModal() == wxID_OK:
                    self.watches.append((dlg.GetValue(), local))
            finally:
                dlg.Destroy()

    def showLoading(self):
        self.load_dict(None, loading=1)

    def load_dict(self, svalues, force=0, loading=0):
        count = self.GetItemCount()
        row = 0
        for name, local in self.watches:
            if svalues:
                svalue = svalues.get(name, '???')
            elif loading:
                svalue = '...'
            else:
                svalue = '???'
            if local:
                idx = 3
            else:
                idx = 4
            if row >= count:
                # Insert.
                self.InsertImageStringItem(row, name, idx)
                count = count + 1
            else:
                # Update.
                self.SetStringItem(row, 0, name, idx)
            self.SetStringItem(row, 1, svalue, idx)
            row = row + 1
        while row < count:
            self.DeleteItem(count - 1)
            count = count - 1

    def OnDelete(self, event):
        sel = self.rightsel
        if sel != -1:
            del self.watches[sel]
            self.DeleteItem(sel)

    def OnDeleteAll(self, event):
        del self.watches[:]
        self.DeleteAllItems()

    def OnExpand(self, event):
        sel = self.rightsel
        if sel != -1:
            name, local = self.watches[sel]
            self.debugger.requestWatchSubobjects(name, local, sel + 1)

##    def OnItemSelect(self, event):
##        self.selected = event.m_itemIndex

##    def OnItemDeselect(self, event):
##        self.selected = -1

    def OnRightDown(self, event):
        self.pos = event.GetPosition()

    def OnRightClick(self, event):
        if not self.pos:
            return
        sel = self.HitTest(self.pos)[0]
        if sel != -1:
            self.rightsel = sel
            self.PopupMenu(self.menu, self.pos)

class DebugStatusBar(wxStatusBar):
    def __init__(self, parent):
        wxStatusBar.__init__(self, parent, -1)
        self.SetFieldsCount(2)

    def proceedAndRequestStatus(self, command, temp_breakpoint=None, args=()):
        # Non-blocking.
        self.sb.updateState(_('Running...'), 'busy')
        if not temp_breakpoint:
            temp_breakpoint = 0
        self.invokeInDebugger('proceedAndRequestStatus',
                              (command, temp_breakpoint, args),
                              'receiveDebuggerStatus')

    def clientFNToServerFN(self, filename):
        """Converts a filename on the client to a filename on the server.

        Currently just turns file URLs into paths.  If you want to be able to
        set breakpoints when running the client in a different environment
        from the server, you'll need to expand this.
        """
        # XXX should we .fncache this? Files changing names are undefined
        # XXX during the lifetime of the debugger

    def writeError(self, message, is_error=1):
        if message and is_error:
            self.error.SetBackgroundColour(wxNamedColour('yellow'))
        else:
            self.error.SetBackgroundColour(wxNamedColour('white'))
        self.error.SetLabel(message)

        rect = self.GetFieldRect(1)
        self.error.SetDimensions(
            rect.x+2, rect.y+2, rect.width-4, rect.height-4)

    def OnSize(self, event):
        rect = self.GetFieldRect(0)
        self.status.SetDimensions(rect.x+2, rect.y+2,
                                  rect.width-4, rect.height-4)
        rect = self.GetFieldRect(1)
        self.error.SetDimensions(rect.x+2, rect.y+2,
                                 rect.width-4, rect.height-4)


def simplifyPathList(data,
                     SequenceTypes=(type(()), type([])),
                     ExcludeTypes=(type(None),) ):
    # Takes a possibly nested structure and turns it into a flat tuple.
    if type(data) in SequenceTypes:
        newdata = []
        for d in data:
            nd = simplifyPathList(d)
            if nd:
                newdata.extend(nd)
        return newdata
    elif type(data) in ExcludeTypes:
        return ()
    else:
        return list(string.split(str(data), os.pathsep))

def compareColors(c1, c2):
    return (c1.Red() == c2.Red() and
            c1.Green() == c2.Green() and
            c1.Blue() == c2.Blue())


wxID_PAGECHANGED = NewId()
wxID_TOPPAGECHANGED = NewId()
class DebuggerFrame(wxFrame):#, Utils.FrameRestorerMixin):
    debug_client = None

    def __init__(self, editor, filename=None, slave_mode=1):
        wxFrame.__init__(self, editor, -1, 'Debugger')

        self.winConfOption = 'debugger'
        self.setDefaultDimensions()

        self.editor = editor
        self.running = 0
        self.slave_mode = slave_mode
        if filename:
            self.setDebugFile(filename)

        self.SetIcon(IS.load('Images/Icons/Debug.ico'))

        self.viewsImgLst = wxImageList(16, 16)
        self.viewsImgLst.Add(IS.load('Images/Debug/Stack.png'))
        self.viewsImgLst.Add(IS.load('Images/Debug/Breakpoints.png'))
        self.viewsImgLst.Add(IS.load('Images/Debug/Watches.png'))
        self.viewsImgLst.Add(IS.load('Images/Debug/Locals.png'))
        self.viewsImgLst.Add(IS.load('Images/Debug/Globals.png'))
        self.viewsImgLst.Add(IS.load('Images/Debug/Output.png'))

        self.invalidatePanes()

        self.sb = DebugStatusBar(self)
        self.SetStatusBar(self.sb)

        self.toolbar = wxToolBar(
            self, -1, style = wxTB_HORIZONTAL|wxNO_BORDER|flatTools)
        self.SetToolBar(self.toolbar)

        self.runId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Debug.png', 'Debug', self.OnDebug)
        self.stepId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Step.png', 'Step', self.OnStep)
        self.overId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Over.png', 'Over', self.OnOver)
        self.outId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Out.png', 'Out', self.OnOut)
        self.pauseId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Pause.png',  'Pause', self.OnPause)
        self.stopId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/Stop.png',  'Stop', self.OnStop)
        self.toolbar.AddSeparator()
        self.sourceTraceId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/SourceTrace-Off.png',  'Trace in source',
          self.OnSourceTrace, '1')
        self.debugBrowseId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/DebugBrowse.png',  'Debug browsing',
          self.OnDebugBrowse, '1')
        self.shellNamespaceId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/ShellDebug.png',  'Eval in shell',
          self.OnDebugNamespace, '1')
        self.toolbar.AddSeparator()
        self.splitOrientId = Utils.AddToolButtonBmpIS(self, self.toolbar,
          'Images/Debug/ShellDebug.png',  'Toggle split orientation',
          self.OnToggleSplitOrient)

        self.setDebugFile(self.filename)

        # Determine the current lineno, filename, and
        # funcname from the stack.

        self.splitter = wxSplitterWindow(self, -1, style=wxSP_NOBORDER | wxSP_3DSASH | wxSP_FULLSASH)

        # Create a Notebook
        use_images = (1 or wxPlatform == '__WXMSW__')
        
        self.nbTop = wxNotebook(self.splitter, wxID_TOPPAGECHANGED)
        if use_images:
            self.nbTop.SetImageList(self.viewsImgLst)
        EVT_NOTEBOOK_PAGE_CHANGED(self.nbTop, wxID_TOPPAGECHANGED,
                                  self.OnUpperPageChange)

        self.stackView = StackViewCtrl(self.nbTop, None, self)

        if use_images:
            self.nbTop.AddPage(self.stackView, 'Stack', imageId = 0)
        else:
            self.nbTop.AddPage(self.stackView, 'Stack')

        self.breakpts = BreakViewCtrl(self.nbTop, self)
        if use_images:
            self.nbTop.AddPage(self.breakpts, 'Breakpoints', imageId = 1)
        else:
            self.nbTop.AddPage(self.breakpts, 'Breakpoints')

        self.outp = wxTextCtrl(self.nbTop, -1, '',
                               style = wxTE_MULTILINE | wxTE_READONLY)
        self.outp.SetBackgroundColour(wxBLACK)
        self.outp.SetForegroundColour(wxWHITE)
        if (not compareColors(self.outp.GetBackgroundColour(), wxBLACK) or
            not compareColors(self.outp.GetForegroundColour(), wxWHITE)):
            # The color setting was ignored.  Use standard colors instead.
            self.outp.SetBackgroundColour(wxWHITE)
            self.outp.SetForegroundColour(wxBLACK)
        self.outp.SetFont(wxFont(9, wxDEFAULT, wxNORMAL, wxNORMAL, false))
        if use_images:
            self.nbTop.AddPage(self.outp, 'Output', imageId = 5)
        else:
            self.nbTop.AddPage(self.outp, 'Output')

        # Create a Notebook
        self.nbBottom = wxNotebook(self.splitter, wxID_PAGECHANGED)
        EVT_NOTEBOOK_PAGE_CHANGED(self.nbBottom, wxID_PAGECHANGED,
                                  self.OnPageChange)

        if use_images:
            self.nbBottom.SetImageList(self.viewsImgLst)

        self.watches = WatchViewCtrl(self.nbBottom, self.viewsImgLst, self)
        if use_images:
            self.nbBottom.AddPage(self.watches, 'Watches', imageId = 2)
        else:
            self.nbBottom.AddPage(self.watches, 'Watches')

        self.locs = NamespaceViewCtrl(self.nbBottom, self.add_watch, 1, 'local')
        if use_images:
            self.nbBottom.AddPage(self.locs, 'Locals', imageId = 3)
        else:
            self.nbBottom.AddPage(self.locs, 'Locals')

        self.globs = NamespaceViewCtrl(
            self.nbBottom, self.add_watch, 0, 'global')

        if use_images:
            self.nbBottom.AddPage(self.globs, 'Globals', imageId = 4)
        else:
            self.nbBottom.AddPage(self.globs, 'Globals')

        self.splitter.SetMinimumPaneSize(40)

        self.splitter.SplitHorizontally(self.nbTop, self.nbBottom)
        self.splitter.SetSashPosition(175)
        self.splitter.SetSplitMode(wxSPLIT_HORIZONTAL)

    def clearStepPos(self):
        if self.lastStepView is not None:
            if hasattr(self.lastStepView, 'clearStepPos'):
                self.lastStepView.clearStepPos(self.lastStepLineno)
            self.lastStepView = None

        self.lastStepView = None
        self.lastStepLineno = -1

        self.stepping_enabled = 1

        EVT_DEBUGGER_OK(self, self.GetId(), self.OnDebuggerOk)
        EVT_DEBUGGER_EXC(self, self.GetId(), self.OnDebuggerException)
        EVT_DEBUGGER_STOPPED(self, self.GetId(), self.OnDebuggerStopped)

        self.stream_timer = wxPyTimer(self.OnStreamTimer)

        EVT_CLOSE(self, self.OnCloseWindow)

    def destroy(self):
        self.viewsImgLst = None
        self.locs.destroy()
        self.globs.destroy()

    def setDefaultDimensions(self):
        self.SetDimensions(0, Preferences.paletteHeight + \
              Preferences.windowManagerTop + Preferences.windowManagerBottom,
              Preferences.inspWidth, Preferences.bottomHeight)

    _sashes_inited = 0
    def initSashes(self):
        if not self._sashes_inited:
            s = self.GetSize()
            if s.x /float(s.y) > 1:
                mode = wxSPLIT_HORIZONTAL
            else:
                mode = wxSPLIT_VERTICAL
            self.splitter.SetSplitMode(mode)
            self.OnToggleSplitOrient(None)
            self._sashes_inited = 1

    def add_watch(self, name, local):
        self.watches.add_watch(name, local)
        self.nbBottom.SetSelection(0)
        self.invalidatePanes()
        self.updateSelectedPane()

    def OnPageChange(self, event):
        sel = event.GetSelection()
        if sel >= 0:
            self.updateSelectedPane(sel)
        event.Skip()

    def invalidatePanes(self):
        self.updated_panes = [0, 0, 0]

    def updateSelectedPane(self, pageno=-1, do_request=1):
        if pageno < 0:
            pageno = self.nbBottom.GetSelection()
        if not self.updated_panes[pageno]:
            frameno = self.stackView.selection
            if pageno == 0:
                self.watches.showLoading()
                if do_request:
                    self.requestWatches(frameno)
            else:
                if pageno==1: self.locs.showLoading()
                else: self.globs.showLoading()
                if do_request:
                    self.requestDict((pageno==1), frameno)

    def requestWatches(self, frameno):
        ws = self.watches.watches
        exprs = []
        for name, local in ws:
            exprs.append({'name':name, 'local':local})
        if exprs:
            self.invokeInDebugger(
                'evaluateWatches', (exprs, frameno), 'receiveWatches')
        else:
            # No exprs, so no request is necessary.
            self.watches.load_dict(None)
            self.updated_panes[0] = 1

    def receiveWatches(self, status):
        frameno = status['frameno']
        if frameno == self.stackView.selection:
            self.updated_panes[0] = 1
            self.watches.load_dict(status['watches'])
        else:
            # Re-request.
            self.updateSelectedPane()

    def requestDict(self, locs, frameno):
        self.invokeInDebugger(
            'getSafeDict', (locs, frameno), 'receiveDict')

    def receiveDict(self, status):
        frameno = status['frameno']
        if frameno == self.stackView.selection:
            if status.has_key('locals'):
                self.updated_panes[1] = 1
                self.locs.load_dict(status['locals'])
            if status.has_key('globals'):
                self.updated_panes[2] = 1
                self.globs.load_dict(status['globals'])
        else:
            # Re-request.
            self.updateSelectedPane()

    def requestWatchSubobjects(self, name, local, pos):
        self.invokeInDebugger(
            'getWatchSubobjects', (name, self.stackView.selection),
            'receiveWatchSubobjects', (name, local, pos))

    def receiveWatchSubobjects(self, subnames, name, local, pos):
        for subname in subnames:
            self.watches.add_watch('%s.%s' % (name, subname), local, pos)
            pos = pos + 1
        self.nbBottom.SetSelection(0)
        self.invalidatePanes()
        self.updateSelectedPane()

    def requestVarValue(self, name):
        self.invokeInDebugger(
            'pprintVarValue', (name, self.stackView.selection),
            'receiveVarValue')

    def receiveVarValue(self, val):
        if val:
            self.editor.statusBar.setHint(val)

    def getVarValue(self, name):
        if not string.strip(name):
            return None
        self._hasReceivedVal = 0
        self._receivedVal = None
        self.invokeInDebugger(
            'pprintVarValue', (name, self.stackView.selection),
            'receiveVarValue2')
        try:
            while not self._hasReceivedVal:
                wxYield()
            return self._receivedVal
        finally:
            del self._hasReceivedVal
            del self._receivedVal

    def receiveVarValue2(self, val):
        self._receivedVal = val
        self._hasReceivedVal = 1


#---------------------------------------------------------------------------

    def setParams(self, params):
        self.params = params

    def setDebugFile(self, filename):
        self.filename = filename
        title = 'Debugger - %s - %s' % (os.path.basename(filename), filename)
        self.SetTitle(title)

    def setTitleInfo(self, info):
        title = 'Debugger - %s' % info
        self.SetTitle(title)

    def setDebugClient(self, client=None):
        if client is None:
            from ChildProcessClient import ChildProcessClient
            client = ChildProcessClient(self)
        self.debug_client = client

    def invokeInDebugger(self, m_name, m_args=(), r_name=None, r_args=()):
        '''
        Invokes a method asynchronously in the debugger,
        possibly expecting a debugger event to be generated
        when finished.
        '''
        self.debug_client.invokeOnServer(m_name, m_args, r_name, r_args)

    def killDebugger(self):
        self.running = 0
        if self.debug_client:
            self.debug_client.kill()
        self.clearViews()

    def OnDebuggerStopped(self, event):
        """Called when a debugger process stops."""
        show_dialog = 0
        if self.running:
            show_dialog = 1
        self.killDebugger()
        if show_dialog:
            wxMessageDialog(
                self, 'The debugger process stopped prematurely.',
                'Debugger stopped',
                wxOK | wxICON_EXCLAMATION | wxCENTRE).ShowModal()

    def OnStreamTimer(self, event=None, force_timer=0):
        self.updateOutputWindow()
        if force_timer or self.nbTop.GetSelection() == 2:
            # The user is looking at the output page.
            self.stream_timer.Start(300, 1)  # One-shot mode.

    def appendToOutputWindow(self, t):
        # Before appending to the output, remove old data.
        outp = self.outp
        cursz = outp.GetLastPosition()
        newsz = cursz + len(t)
        if newsz >= TEXTCTRL_MAXLEN:
            olddata = outp.GetValue()[newsz - TEXTCTRL_GOODLEN:]
            outp.SetValue(olddata)
        outp.AppendText(t)

    def updateOutputWindow(self):
        while self.debug_client:
            info = self.debug_client.pollStreams()
            if info:
                stdout_text, stderr_text = info
                if stdout_text:
                    self.appendToOutputWindow(stdout_text)
                if stderr_text:
                    self.appendToOutputWindow(stderr_text)
                if not stdout_text and not stderr_text:
                    break
            else:
                break

    def OnUpperPageChange(self, event):
        sel = event.GetSelection()
        if sel == 2:
            # Selected the output window.
            self.OnStreamTimer(None, 1)
        event.Skip()

    def OnDebuggerOk(self, event):
        self.enableStepping()
        receiver_name = event.GetReceiverName()
        if receiver_name is not None:
            rcv = getattr(self, receiver_name)
            apply(rcv, (event.GetResult(),) + event.GetReceiverArgs())

    def OnDebuggerException(self, event):
        self.enableStepping()
        t, v = event.GetExc()
        if hasattr(t, '__name__'):
            t = t.__name__
        # TODO?: Use wxScrolledMessageDialog  (note that it lacks
        # wxYES_NO support.)
        msg = '%s: %s.' % (t, v)
        if len(msg) > 100:
            msg = msg[:100] + '...'
        confirm = (wxMessageDialog(
            self, msg + ' Stop debugger?',
            'Debugger Communication Exception',
            wxYES_NO | wxYES_DEFAULT | wxICON_EXCLAMATION |
            wxCENTRE).ShowModal() == wxID_YES)

        if confirm:
            self.killDebugger()

    def runProcess(self, autocont=0):
        self.running = 1
        self.sb.writeError('Waiting...', 0)
        brks = bplist.getBreakpointList()
        for brk in brks:
            brk['filename'] = self.clientFNToServerFN(brk['filename'])
        if self.slave_mode:
            # Work with a child process.
            add_paths = simplifyPathList(pyPath)
            add_paths = map(self.clientFNToServerFN, add_paths)
            filename = self.clientFNToServerFN(self.filename)
            self.invokeInDebugger(
                'runFileAndRequestStatus',
                (filename, self.params or [], autocont, add_paths, brks),
                'receiveDebuggerStatus')
        else:
            # Work with a peer or remote process.
            self.invokeInDebugger(
                'setupAndRequestStatus',
                (autocont, brks),
                'receiveDebuggerStatus')

        # InProcessClient TODO: setup the execution environment
        # the way it used to be done.

    def proceedAndRequestStatus(self, command, temp_breakpoint=None):
        # Non-blocking.
        self.sb.writeError('Running...', 0)
        if not temp_breakpoint:
            temp_breakpoint = 0
        self.invokeInDebugger('proceedAndRequestStatus',
                              (command, temp_breakpoint),
                              'receiveDebuggerStatus')

    def clientFNToServerFN(self, filename):
        """Converts a filename on the client to a filename on the server.

        Currently just turns file URLs into paths.  If you want to be able to
        set breakpoints when running the client in a different environment
        from the server, you'll need to expand this.
        """
        if filename.startswith('file://'):
            return filename[7:]
        else:
            return filename

    def serverFNToClientFN(self, filename):
        """Converts a filename on the server to a filename on the client.

        Currently just generates URLs.  If you want to be able to
        set breakpoints when running the client in a different environment
        from the server, you'll need to expand this.
        """
        if filename.find('://') < 0:
            return 'file://' + filename
        else:
            return filename

    def deleteBreakpoints(self, filename, lineno):
        fn = self.clientFNToServerFN(filename)
        self.invokeInDebugger('clearBreakpoints', (fn, lineno))
        self.breakpts.refreshList()

    def setBreakpoint(self, filename, lineno, tmp):
        fn = self.clientFNToServerFN(filename)
        self.invokeInDebugger('addBreakpoint', (fn, lineno, tmp))
        self.breakpts.refreshList()

    def requestDebuggerStatus(self):
        self.sb.writeError('Waiting...', 0)
        self.invokeInDebugger('getStatusSummary', (),
                              'receiveDebuggerStatus')

    def receiveDebuggerStatus(self, info):
        # Get stdout and stderr if available.
        data = info.get('stdout', None)
        if data:
            self.appendToOutputWindow(data)
        data = info.get('stderr', None)
        if data:
            self.appendToOutputWindow(data)

        # Translate server filenames to client filenames.
        stack = info['stack']
        for frame in stack:
            frame['client_filename'] = self.serverFNToClientFN(
                frame['filename'])

        # Determine the current lineno, filename, and
        # funcname from the stack.
        if stack:
            bottom = stack[-1]
            filename = bottom['filename']
            funcname = bottom['funcname']
            lineno = bottom['lineno']
            base = os.path.basename(filename)
        else:
            filename = funcname = lineno = base = ''

        self.running = info['running']

        # Show running status.
        if self.running:
            message = "%s:%s" % (base, lineno)
            if funcname != "?":
                message = "%s: %s()" % (message, funcname)
        else:
            ## Close
            ##if self.debug_client:
            ##    self.debug_client.kill()
            ##    self.debug_client = None
            message = 'Finished.'
        self.sb.status.SetLabel(message)

        # Show exception information.
        exc_type = info.get('exc_type', None)
        exc_value = info.get('exc_value', None)
        if exc_type is not None:
            m1 = exc_type
            if exc_value is not None:
                try:
                    m1 = "%s: %s" % (m1, exc_value)
                except:
                    pass
            bg = wxNamedColour('yellow')
        else:
            m1 = ''
            bg = wxNamedColour('white')#self.errorbg
        self.sb.writeError(m1)

        # Load the stack view.
        sv = self.stackView
        if sv:
            i = info['frame_stack_len']
            sv.load_stack(stack, i)
            sv.selectCurrentEntry()

        # If at a breakpoint, display status.
        if bplist.hasBreakpoint(filename, lineno):
            bplist.clearTemporaryBreakpoints(filename, lineno)
            self.sb.error.SetBackgroundColour(wxNamedColour('red'))
            self.sb.error.SetLabel('Breakpoint.')
            rect = self.sb.GetFieldRect(1)
            self.sb.error.SetDimensions(rect.x+2, rect.y+2,
                                        rect.width-4, rect.height-4)

        # Update breakpoints view with stats.
        self.breakpts.stats = info['breaks']
        for item in self.breakpts.stats:
            item['client_filename'] = self.serverFNToClientFN(
                item['filename'])
        self.breakpts.refreshList()
        self.selectSourceLine(filename, lineno)

        # All info in watches, locals, and globals panes is now invalid.
        self.invalidatePanes()
        # Update the currently selected pane.
        self.updateSelectedPane()
        # Receive stream data even if the user isn't looking.
        self.updateOutputWindow()

    def clearStepPos(self):
        if self.lastStepView is not None:
            self.lastStepView.clearStepPos(self.lastStepLineno)
            self.lastStepView = None

    def selectSourceLine(self, filename, lineno):
        if self.isSourceTracing():
            self.clearStepPos()
            if not filename:
                return

            #self.editor.SetFocus()
            self.editor.openOrGotoModule(filename)
            model = self.editor.getActiveModulePage().model
            sourceView = model.views['Source']
            sourceView.focus(false)
            #sourceView.SetFocus()
            sourceView.selectLine(lineno - 1)
            sourceView.setStepPos(lineno - 1)
            self.lastStepView = sourceView
            self.lastStepLineno = lineno - 1

    def enableTools(self, enable = true):
        self.toolbar.EnableTool(self.runId, enable)
        self.toolbar.EnableTool(self.stepId, enable)
        self.toolbar.EnableTool(self.overId, enable)
        self.toolbar.EnableTool(self.outId, enable)
        self.toolbar.EnableTool(self.stopId, enable)

    def isSourceTracing(self):
        return self.toolbar.GetToolState(self.sourceTraceId)

    def isDebugBrowsing(self):
        return self.toolbar.GetToolState(self.debugBrowseId)

    def isInShellNamepace(self):
        return self.toolbar.GetToolState(self.shellNamespaceId)

    def isRunning(self):
        return self.running

    def ensureRunning(self, cont_if_running=0, cont_always=0,
                      temp_breakpoint=None):
        if self.isRunning():
            if cont_if_running or cont_always:
                self.doDebugStep('set_continue', temp_breakpoint)
        else:
            # Assume temp. breakpoint is already in bplist.
            self.runProcess(cont_always)

    def enableStepping(self):
        # TODO: enable the step buttons.
        self.stepping_enabled = 1

    def disableStepping(self):
        # TODO: disable the step buttons.
        self.stepping_enabled = 0

    def doDebugStep(self, method=None, temp_breakpoint=None):
        if self.stepping_enabled:
            self.disableStepping()
            self.clearStepPos()
            self.invalidatePanes()
            self.updateSelectedPane(do_request=0)
            if not self.isRunning():
                self.runProcess()
            elif method:
                self.proceedAndRequestStatus(method, temp_breakpoint)
        else:
            if temp_breakpoint:
                self.setBreakpoint(temp_breakpoint[0],
                                   temp_breakpoint[1], 1)

    def OnDebug(self, event):
        self.doDebugStep('set_continue')

    def OnStep(self, event):
        self.doDebugStep('set_step')

    def OnOver(self, event):
        self.doDebugStep('set_step_over')

    def OnOut(self, event):
        self.doDebugStep('set_step_out')

    def OnPause(self, event):
        # Only meaningful when running.
        if not self.stepping_enabled:
            self.invokeInDebugger('set_pause')

    def OnStop(self, event):
        self.clearStepPos()
        self.enableStepping()
        self.invalidatePanes()
        self.updateSelectedPane(do_request=0)
        self.proceedAndRequestStatus('set_quit')

    def OnToolOver(self, event):
        pass


    def clearViews(self):
        self.clearStepPos()
        self.stackView.load_stack([])
        self.watches.load_dict({})
        self.locs.load_dict({})
        self.globs.load_dict({})
        self.sb.writeError('', 0)

    def OnCloseWindow(self, event):
        try:
            self.killDebugger()
##            self.locs.destroy()
##            self.globs.destroy()
##            self.breakpts.destroy()
##            self.watches.destroy()
        finally:
##            self.Destroy()
            self.debug_client = None
            try: self.editor.debugger = None
            except: pass
            self.editor = None
            self.Show(0)
            event.Skip()

    def isInShellNamepace(self):
        return self.toolbar.GetToolState(self.shellNamespaceId)

    def OnDebugNamespace(self, event):
        self.editor.OnSwitchShell(None)
        self.editor.shell.debugShell(self.isInShellNamepace(), self)

    def OnToggleSplitOrient(self, event):
        if self.splitter.GetSplitMode() == wxSPLIT_HORIZONTAL:
            self.splitter.SetSplitMode(wxSPLIT_VERTICAL)
            self.splitter.SplitVertically(self.nbTop, self.nbBottom)
            sashpos = self.splitter.GetClientSize().x / 2
        else:
            self.splitter.SetSplitMode(wxSPLIT_HORIZONTAL)
            self.splitter.SplitHorizontally(self.nbTop, self.nbBottom)
            sashpos = self.splitter.GetClientSize().y / 2
        self.splitter.SetSashPosition(sashpos)
