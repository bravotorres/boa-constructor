#!/usr/bin/env python  
#----------------------------------------------------------------------
# Name:        Boa.py
# Purpose:     The main file for Boa.
#
# Author:      Riaan Booysen
#
# Created:     1999
# RCS-ID:      $Id$
# Copyright:   (c) 1999 - 2001 Riaan Booysen
# Licence:     GPL
#----------------------------------------------------------------------
#Boa:App:BoaApp

# Once upon a time
# the story starts
# in a few files far away


import sys, os, string

def trace_func(frame, event, arg):
    """ Callback function when Boa runs in tracing mode"""
    if frame:
        info = '%s|%d|%d|%s|%s\n' % (frame.f_code.co_filename, frame.f_lineno, id(frame), event, `arg`)
        tracefile.write(info)
        tracefile.flush()
    return trace_func

def get_current_frame():
    try:
        1 + ''  # raise an exception
    except:
        return sys.exc_info()[2].tb_frame

startupErrors = []

# Command line options
doDebug = 0
startupfile = ''
startupModules = ()
if len(sys.argv) > 1:
    import getopt
    optlist, args = getopt.getopt(sys.argv[1:], 'DTs')
    if ('-D', '') in optlist and len(args):
        doDebug = 1
    elif ('-T', '') in optlist:
        tracefile = open('Boa.trace', 'wt')
        tracefile.write(os.getcwd()+'\n')
        trace_func(get_current_frame(), 'call', None)
        sys.setprofile(trace_func)
    elif ('-s', '') in optlist:
        pass
    elif len(args):
        # XXX Only the first file appears in the list when multiple files
        # XXX are drag/dropped on a Boa shortcut, why?
        startupModules = args

    if ('-s', '') in optlist:
        startupfile = os.environ.get('BOASTARTUP') or \
                      os.environ.get('PYTHONSTARTUP')

# Custom installations

# Only install if it's not a 'binary' distribution
import wxPython
if hasattr(wxPython, '__file__'):
    boaPath = os.path.abspath(os.path.join(os.getcwd(), sys.path[0]))
    wxPythonLibPath = os.path.join(os.path.dirname(wxPython.__file__), 'lib')
    # Install anchors if necessary
    try:
        import wxPython.lib.anchors
    except ImportError:
        print 'installing Anchors'
        import shutil
        shutil.copy(os.path.join(boaPath, 'anchors.py'), wxPythonLibPath)
        import wxPython.lib.anchors

import Preferences
from wxPython.wx import *
import About
import Utils

if Preferences.installBCRTL and hasattr(wxPython, '__file__'):
    try:
        # Install/update run time libs if necessary
        Utils.updateDir(os.path.join(boaPath, 'bcrtl'),
             os.path.join(wxPythonLibPath, 'bcrtl'))
    except Exception, error:
        startupErrors.extend(['Error while installing Run Time Libs:',
        '    '+str(error), 
        'Make sure you have sufficient rights to copy these files, and that ',
        'the files are not read only. You may turn off this attempted ',
        'installation in Preferences.py'])

# XXX Remaining milestones before alpha
# XXX auto created frames (main frame handled currently)
# XXX More property editors!
# XXX More companion classes! $
# XXX Controllers for the Editor MVC
# XXX Debugger merged (but optional)
# XXX New Docs framework

# XXX Find: Exceptions should not cancel the search
# XXX Editor should store file names internally in lowercase so that opening
# XXX from differing filepaths open the same file (M$~1 etc not handled)

# XXX Mechanism to detect file date changes external of boa
# XXX Possibly on Explorer level, checking before saving on systems where
# XXX getting a time stamp makes sense and is available

# XXX Refactor PropertyEditor/Companion/Inspector interfaces

# XXX Support IDLE extensions

# XXX Fix transport layer
# XXX     Rename updates (both ways)

# XXX Code completion
# XXX     self.qwerty = qwerty
# XXX     wipes '= qwerty' when qwerty is selected

# XXX Renaming Boa.jpg in root fails

# XXX STC: The Python demo is fast!, look for speedups

# XXX Save as after app is closed

modules ={'About': [0, 'About box and Splash screen', 'About.py'],
 'AppViews': [0, 'Views for the AppModel', 'Views/AppViews.py'],
 'BaseCompanions': [0, '', 'Companions/BaseCompanions.py'],
 'Browse': [0, 'History for navigation through the IDE', 'Browse.py'],
 'CVSExplorer': [0, '', 'Explorers/CVSExplorer.py'],
 'CVSResults': [0, '', 'Explorers/CVSResults.py'],
 'ClassBrowser': [0,
                  'Frame that displays the wxPython object hierarchy by Class and Module',
                  'ClassBrowser.py'],
 'CollectionEdit': [0, '', 'Views/CollectionEdit.py'],
 'ComCompanions': [0,
                   'Companion classes for COM (win32 only)',
                   'Companions/ComCompanions.py'],
 'Companions': [0,
                'Most visual wxPython class companions ',
                'Companions/Companions.py'],
 'Constructors': [0,
                  'Constructor signature mixin classes',
                  'Companions/Constructors.py'],
 'Controllers': [0, 'Controllers for the Models and Views', 'Controllers.py'],
 'CtrlAlign': [0, 'Aligns a group of controls', 'CtrlAlign.py'],
 'CtrlSize': [0, 'Sizes a group of controls', 'CtrlSize.py'],
 'DAVExplorer': [0, '', 'Explorers/DAVExplorer.py'],
 'DataView': [0,
              'View to manage non visual frame objects',
              'Views/DataView.py'],
 'Debugger': [0,
              'Module for in-process debugging of wxPython and Python apps',
              'Debugger/Debugger.py'],
 'Designer': [0, 'View to visually design frames', 'Views/Designer.py'],
 'DialogCompanions': [0, '', 'Companions/DialogCompanions.py'],
 'DiffView': [0, '', 'Views/DiffView.py'],
 'Editor': [0, 'Source code editor hosting models and views', 'Editor.py'],
 'EditorExplorer': [0, '', 'Explorers/EditorExplorer.py'],
 'EditorHelper': [0, 'Module defining Editor constants', 'EditorHelper.py'],
 'EditorModels': [0,
                  'Model classes. Models loosely represent source types.',
                  'EditorModels.py'],
 'EditorUtils': [0,
                 'Specialised ToolBar and StatusBar controls for the Editor',
                 'EditorUtils.py'],
 'EditorViews': [0,
                 'Main module for View classes that work with Models',
                 'Views/EditorViews.py'],
 'Enumerations': [0, '', 'PropEdit/Enumerations.py'],
 'ErrorStack': [0, 'Various forms of error parsers', 'ErrorStack.py'],
 'ErrorStackFrm': [0, '', 'ErrorStackFrm.py'],
 'EventCollections': [0, '', 'Companions/EventCollections.py'],
 'Explorer': [0,
              'Specialised visual controls for the Explorer (Tree, list and splitter)',
              'Explorers/Explorer.py'],
 'ExplorerNodes': [0, '', 'Explorers/ExplorerNodes.py'],
 'ExtMethDlg': [0, 'Dialog for ExternalMethods', 'ZopeLib/ExtMethDlg.py'],
 'FTPExplorer': [0, '', 'Explorers/FTPExplorer.py'],
 'FileDlg': [0, 'Replacement for the standard file dialog. ', 'FileDlg.py'],
 'FileExplorer': [0, '', 'Explorers/FileExplorer.py'],
 'GCFrame': [0, '', 'GCFrame.py'],
 'HTMLCyclops': [0, '', 'HTMLCyclops.py'],
 'HTMLResponse': [0, '', 'HTMLResponse.py'],
 'Help': [0, 'Interactive help frame', 'Help.py'],
 'HelpCompanions': [0, '', 'Companions/HelpCompanions.py'],
 'ImageStore': [0,
                'Centralised point to load images (cached/zipped/etc)',
                'ImageStore.py'],
 'ImageViewer': [0, '', 'ZopeLib/ImageViewer.py'],
 'Infofields': [0, '', 'Infofields.py'],
 'InspectableViews': [0, '', 'Views/InspectableViews.py'],
 'Inspector': [0,
               "Inspects object's constructor/properties/events/parents",
               'Inspector.py'],
 'InspectorEditorControls': [0, '', 'PropEdit/InspectorEditorControls.py'],
 'LoginDialog': [0, '', 'ZopeLib/LoginDialog.py'],
 'ModRunner': [0,
               'Module that runs processes in a variety of ways',
               'ModRunner.py'],
 'OGLViews': [0, '', 'Views/OGLViews.py'],
 'ObjCollection': [0, '', 'Views/ObjCollection.py'],
 'Palette': [1,
             'Top frame which hosts the component palette and help options',
             'Palette.py'],
 'PaletteMapping': [0, '', 'PaletteMapping.py'],
 'PaletteStore': [0,
                  'Storage for variables defining the palette organisation',
                  'PaletteStore.py'],
 'PhonyApp': [0, '', 'PhonyApp.py'],
 'Preferences': [0,
                 'Central store of customiseable properties',
                 'Preferences.py'],
 'PrefsExplorer': [0, '', 'Explorers/PrefsExplorer.py'],
 'PrefsGTK': [0, 'Unix specific preference settings', 'PrefsGTK.py'],
 'PrefsKeys': [0, 'Keyboard bindings', 'PrefsKeys.py'],
 'PrefsMSW': [0, 'Windows specific preference settings', 'PrefsMSW.py'],
 'ProcessProgressDlg': [0, '', 'ProcessProgressDlg.py'],
 'ProfileView': [0, '', 'Views/ProfileView.py'],
 'PropDlg': [0, '', 'ZopeLib/PropDlg.py'],
 'PropertyEditors': [0,
                     'Module defining property editors used in the Inspector',
                     'PropEdit/PropertyEditors.py'],
 'PySourceView': [0, '', 'Views/PySourceView.py'],
 'PythonInterpreter': [0, '', 'ExternalLib/PythonInterpreter.py'],
 'RTTI': [0, 'Introspection code. Run time type info', 'RTTI.py'],
 'RunCyclops': [0, '', 'RunCyclops.py'],
 'SSHExplorer': [0, '', 'Explorers/SSHExplorer.py'],
 'Search': [0, '', 'Search.py'],
 'SelectionTags': [0,
                   'Controls and objects that manage the visual selection in the Designer',
                   'Views/SelectionTags.py'],
 'ShellEditor': [0, 'Python Interpreter Shell window', 'ShellEditor.py'],
 'SourceViews': [0, '', 'Views/SourceViews.py'],
 'StyledTextCtrls': [0,
                     'Mixin classes to use features of Scintilla',
                     'Views/StyledTextCtrls.py'],
 'Tests': [0, '', 'Tests.py'],
 'UserCompanions': [0, '', 'Companions/UserCompanions.py'],
 'UtilCompanions': [0, '', 'Companions/UtilCompanions.py'],
 'Utils': [0, 'General utility routines and classes', 'Utils.py'],
 'XMLView': [0, '', 'Views/XMLView.py'],
 'ZipExplorer': [0, '', 'Explorers/ZipExplorer.py'],
 'ZopeCompanions': [0, '', 'Companions/ZopeCompanions.py'],
 'ZopeEditorModels': [0,
                      'Editor models for Zope objects',
                      'ZopeEditorModels.py'],
 'ZopeExplorer': [0, '', 'Explorers/ZopeExplorer.py'],
 'ZopeFTP': [0, '', 'ZopeLib/ZopeFTP.py'],
 'ZopeViews': [0, '', 'Views/ZopeViews.py'],
 'methodparse': [0,
                 'Module responsible for parsing code inside generated methods',
                 'methodparse.py'],
 'moduleparse': [0,
                 'For parsing a whole module into Module, classes and functions',
                 'moduleparse.py'],
 'ndiff': [0, '', 'ExternalLib/ndiff.py'],
 'popen2import': [0, '', 'popen2import.py'],
 'relpath': [0, '', 'relpath.py'],
 'sender': [0, '', 'sender.py'],
 'sourceconst': [0, 'Source generation constants', 'sourceconst.py']}

class BoaApp(wxApp):
    """ Application object, responsible for the Splash screen, command line
        switches, optional logging and creation of the main frames. """

    def __init__(self, redirect=false):
        wxApp.__init__(self, redirect)

    def OnInit(self):
        wxInitAllImageHandlers()

        wxToolTip_Enable(true)

        abt = About.createSplash(None)
        abt.Show(true)
        try:
            # Let the splash screen repaint
            wxYield()
            import Palette

            print 'creating Palette'
            self.main = Palette.BoaFrame(None, -1, self)

            self.main.Show(true)
            self.SetTopWindow(self.main)

            self.main.inspector.Show(true)
            # For some reason the splitters have to be visible on GTK before they
            # can be sized.
            self.main.inspector.initSashes()
            self.main.editor.Show(true)

            # Call startup files after complete editor initialisation
            self.main.editor.shell.execStartupScript(startupfile)            
        finally:
            abt.Destroy()
            del abt

        # Open info text files if run for the first time
        if os.path.exists('1stTime'):
            try:
                self.main.editor.openOrGotoModule('README.txt')
                self.main.editor.openOrGotoModule('Changes.txt')
                os.remove('1stTime')
            except:
                print 'Could not load intro text files'

        # Apply command line switches
        if doDebug:
            mod = self.main.editor.openModule(args[0])
            mod.debug()
        elif startupModules:
            for mod in startupModules:
                self.main.editor.openModule(mod)

        Utils.showTip(self.main.editor)

        if Preferences.logStdStreams:
            sys.stderr = Utils.ErrorLoggerPF()
            sys.stdout = Utils.OutputLoggerPF()

        if startupErrors:
            for error in startupErrors:
                wxLogError(error)
            wxLogError('There were errors during startup, click "Details" for more...')

        return true


def main():
    app = BoaApp(0)
    app.quit = false
    while not app.quit:
        app.MainLoop()

if __name__ == '__main__' or hasattr(wxApp, 'debugger'):
    main()
 