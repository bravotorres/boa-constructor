#-----------------------------------------------------------------------------
# Name:        PrefsExplorer.py
# Purpose:
#
# Author:      Riaan Booysen
#
# Created:     2001/06/08
# RCS-ID:      $Id$
# Copyright:   (c) 2001 - 2002
# Licence:     GPL
#-----------------------------------------------------------------------------
print 'importing Explorers.PrefsExplorer'
import string, os, sys, glob, pprint, imp
import types

from wxPython import wx
true=1;false=0

#sys.path.append('..')
import ExplorerNodes, Preferences, Utils
from Models import EditorHelper
from Views import STCStyleEditor
import methodparse

class PreferenceGroupNode(ExplorerNodes.ExplorerNode):
    """ Represents a group of preference collections """
    protocol = 'prefs.group'
    defName = 'PrefsGroup'
    def __init__(self, name, parent):
        ExplorerNodes.ExplorerNode.__init__(self, name, name, None,
              EditorHelper.imgPrefsFolder, None)

        self.vetoSort = true
        self.preferences = []

    def isFolderish(self):
        return true

    def openList(self):
        return self.preferences

    def notifyBeginLabelEdit(self, event):
        event.Veto()

class BoaPrefGroupNode(PreferenceGroupNode):
    """ The Preference node in the Explorer """
    protocol = 'boa.prefs.group'
    customPrefs = [] # list of tuples ('name', 'file')
    def __init__(self, parent):
        PreferenceGroupNode.__init__(self, 'Preferences', parent)
        self.bold = true

        prefImgIdx = EditorHelper.imgSystemObj
        stcPrefImgIdx = EditorHelper.imgPrefsSTCStyles

        self.source_pref = PreferenceGroupNode('Source', self)

        self.source_pref.preferences = [
            UsedModuleSrcBsdPrefColNode('Default settings',
                Preferences.exportedSTCProps, os.path.join(Preferences.rcPath,
                'prefs.rc.py'), prefImgIdx, self, Preferences, false)]

        for name, lang, STCClass, stylesFile in ExplorerNodes.langStyleInfoReg:
            if not os.path.isabs(stylesFile):
                stylesFile = os.path.join(Preferences.rcPath, stylesFile)
            self.source_pref.preferences.append(STCStyleEditPrefsCollNode(
                  name, lang, STCClass, stylesFile, stcPrefImgIdx, self))
        self.preferences.append(self.source_pref)

        self.general_pref = UsedModuleSrcBsdPrefColNode('General',
            Preferences.exportedProperties, os.path.join(Preferences.rcPath,
            'prefs.rc.py'), prefImgIdx, self, Preferences)
        self.preferences.append(self.general_pref)

        self.platform_pref = UsedModuleSrcBsdPrefColNode('Platform spesific',
            Preferences.exportedProperties2, os.path.join(Preferences.rcPath,
            'prefs.%s.rc.py' % (wx.wxPlatform == '__WXMSW__' and 'msw' or 'gtk')),
            prefImgIdx, self, Preferences)
        self.preferences.append(self.platform_pref)

        self.keys_pref = KeyDefsSrcPrefColNode('Key bindings', ('*',),
            os.path.join(Preferences.rcPath, 'prefskeys.rc.py'), prefImgIdx,
            self, Preferences.keyDefs)
        self.preferences.append(self.keys_pref)

        for name, filename in self.customPrefs:
            if not os.path.isabs(filename):
                filename = os.path.join(Preferences.rcPath, filename)
            self.preferences.append(UsedModuleSrcBsdPrefColNode(name,
            ('*',), filename, prefImgIdx, self, Preferences))

##        self.pychecker_pref = SourceBasedPrefColNode('PyChecker',
##            ('*',), Preferences.pyPath+'/.pycheckrc', prefImgIdx, self)
##        self.preferences.append(self.pychecker_pref)

        self.plugin_pref = PreferenceGroupNode('Plug-ins', self)

        self.core_plugpref = UsedModuleSrcBsdPrefColNode('Core support',
            Preferences.exportedPluginProps, os.path.join(Preferences.rcPath,
            'prefs.rc.py'), prefImgIdx, self, Preferences, false)
        self.files_plugpref = PluginFilesGroupNode()
        self.transp_plugpref = PreferenceGroupNode('Transports', self)
        self.transp_plugpref.preferences = [
            TransportPluginsLoadOrderGroupNode(),
            TransportPluginsTreeDisplayOrderGroupNode(),
        ]

        self.plugin_pref.preferences = [
            self.core_plugpref,
            self.files_plugpref,
            self.transp_plugpref,
        ]

        self.preferences.insert(1, self.plugin_pref)

class PreferenceCollectionNode(ExplorerNodes.ExplorerNode):
    """ Represents an inspectable preference collection """
    protocol = 'prefs'
    def __init__(self, name, props, resourcepath, imgIdx, parent):
        ExplorerNodes.ExplorerNode.__init__(self, name, resourcepath, None,
              imgIdx, None, props)

    def open(self, editor):
        """ Populate inspector with preference items """
        comp = PreferenceCompanion(self.name, self)
        comp.updateProps()

        # Select in inspector
        editor.inspector.restore()
        if editor.inspector.pages.GetSelection() != 1:
            editor.inspector.pages.SetSelection(1)
        editor.inspector.selectObject(comp, false)
        return None, None

    def isFolderish(self):
        return false

    def load(self):
        raise 'Not implemented'

    def save(self, filename, data):
        pass

    def notifyBeginLabelEdit(self, event):
        event.Veto()

class STCStyleEditPrefsCollNode(PreferenceCollectionNode):
    protocol = 'stc.prefs'
    def __init__(self, name, lang, STCclass, resourcepath, imgIdx, parent):
        PreferenceCollectionNode.__init__(self, name, {}, resourcepath, imgIdx, parent)
        self.language = lang
        self.STCclass = STCclass

    def open(self, editor):
        # build list of all open STC's in the Editor
        openSTCViews = []
        for modPge in editor.modules.values():
            for view in modPge.model.views.values():
                if isinstance(view, self.STCclass):
                    openSTCViews.append(view)
        # also check the shell
        if isinstance(editor.shell, self.STCclass):
            openSTCViews.append(editor.shell)
        dlg = STCStyleEditor.STCStyleEditDlg(editor, self.name, self.language,
              self.resourcepath, openSTCViews)
        try: dlg.ShowModal()
        finally: dlg.Destroy()

        return None, None

    def getURI(self):
        return '%s://%s' %(PreferenceCollectionNode.getURI(self), self.language)


class SourceBasedPrefColNode(PreferenceCollectionNode):
    """ Preference collection represented by the global names in python module

    Only names which are also defined in properties are returned
    except when properties is a special match all tuple; ('*',)

    This only applies to names assigned to values ( x = 123 ) not to global
    names defined by classes functions and imports.
    """
    def __init__(self, name, props, resourcepath, imgIdx, parent, showBreaks=true):
        PreferenceCollectionNode.__init__(self, name, props, resourcepath,
              imgIdx, parent)
        self.showBreakLines = showBreaks

    def load(self):
        # All preferences are local
        import moduleparse

        module = moduleparse.Module(self.name,
              open(self.resourcepath).readlines())

        values = []
        comments = []
        options = []
        # keep only names defined in the property list
        for name in module.global_order[:]:
            if name[0] == '_' or self.properties != ('*',) and \
                  name not in self.properties:
                module.global_order.remove(name)
                del module.globals[name]
            else:
                # XXX Should handle multiline assign
                code = string.join(module.source[\
                      module.globals[name].start-1 : \
                      module.globals[name].end], '\n')

                # Extract value
                s = string.find(code, '=')
                if s != -1:
                    values.append(string.strip(code[s+1:]))
                else:
                    values.append('')

                # Read possible comment/help or options
                comment = []
                option = ''
                idx = module.globals[name].start-2
                while idx >= 0:
                    line = string.strip(module.source[idx])
                    if len(line) > 11 and line[:11] == '## options:':
                        option = string.strip(line[11:])
                        idx = idx - 1
                    elif len(line) > 8 and line[:8] == '## type:':
                        option = string.strip('##'+line[8:])
                        idx = idx - 1
                    elif line and line[0] == '#':
                        comment.append(string.lstrip(line[1:]))
                        idx = idx - 1
                    else:
                        break
                comment.reverse()
                comments.append(string.join(comment, '\n'))
                options.append(option)

        if self.showBreakLines: breaks = module.break_lines
        else: breaks = {}

        return (module.global_order, values, module.globals, comments, options,
                breaks)

    def save(self, filename, data):
        """ Updates one property """
        src = open(self.resourcepath).readlines()
        src[data[2].start-1] = '%s = %s\n' % (data[0], data[1])
        open(self.resourcepath, 'w').writelines(src)

class UsedModuleSrcBsdPrefColNode(SourceBasedPrefColNode):
    """ Also update the value of a global attribute of an imported module """
    def __init__(self, name, props, resourcepath, imgIdx, parent, module,
          showBreaks=true):
        SourceBasedPrefColNode.__init__(self, name, props, resourcepath, imgIdx,
              parent, showBreaks)
        self.module = module

    def save(self, filename, data):
        SourceBasedPrefColNode.save(self, filename, data)
        if hasattr(self.module, data[0]):
            setattr(self.module, data[0], eval(data[1], vars(Preferences)))

class KeyDefsSrcPrefColNode(PreferenceCollectionNode):
    """ Preference collection representing the key bindings """
    def __init__(self, name, props, resourcepath, imgIdx, parent, keyDefs):
        PreferenceCollectionNode.__init__(self, name, props, resourcepath,
              imgIdx, parent)
        self.showBreakLines = true
        self._editor = None

    def open(self, editor):
        PreferenceCollectionNode.open(self, editor)
        self._editor = editor

    def load(self):
        import moduleparse

        src = open(self.resourcepath).readlines()
        module = moduleparse.Module(self.name, src)

        # find keydefs
        keydefs = {}
        names = []
        values = []
        start = end = idx = -1
        for line in src:
            idx = idx + 1
            line = string.strip(line)
            if line == 'keyDefs = {':
                start = idx
            elif start != -1 and line:
                if line[-1] == '}':
                    end = idx
                    break
                elif line[0] != '#':
                    colon = string.find(line, ':')
                    if colon == -1: raise Exception('Invalid KeyDef item: %s'%line)
                    name = string.rstrip(line[:colon])[1:-1]
                    val = string.lstrip(line[colon+1:])
                    keydefs[name] = moduleparse.CodeBlock(val, idx+1, idx+1)
                    names.append(name)
                    values.append(val)

        return (names, values, keydefs, ['']*len(keydefs),
              ['## keydef']*len(keydefs), module.break_lines)

    def save(self, filename, data):
        """ Updates one key:val in keydefs dict """

        # Update source file
        src = open(self.resourcepath).readlines()
        src[data[2].start-1] = \
              "  '%s'%s: %s\n" % (data[0], (12 - len(data[0]))*' ', data[1])
        open(self.resourcepath, 'w').writelines(src)
        # Update dictionary
        Preferences.keyDefs[data[0]] = eval(data[1], vars(Preferences))[0]
        # Update editor menus
        self._editor.setupToolBar()
        self._editor.updateStaticMenuShortcuts()
        self._editor.shell.bindShortcuts()


class ConfigBasedPrefsColNode(PreferenceCollectionNode):
    """ Preferences driven by config files """
    pass


#---Companions------------------------------------------------------------------

from PropEdit import PropertyEditors, InspectorEditorControls

class KeyDefConfPropEdit(PropertyEditors.ConfPropEdit):
    def inspectorEdit(self):
        self.editorCtrl = InspectorEditorControls.ButtonIEC(self, self.value)
        self.editorCtrl.createControl(self.parent, self.idx, self.width, self.edit)

    def edit(self, event):
        import KeyDefsDlg
        dlg = KeyDefsDlg.KeyDefsDialog(self.parent, self.name, self.value)
        try:
            if dlg.ShowModal() == wx.wxID_OK:
                self.editorCtrl.value = dlg.result
                self.inspectorPost(false)
        finally:
            dlg.Destroy()

    def getDisplayValue(self):
        try:
            return eval(self.value, wx.__dict__)[0][2]
        except Exception, err:
            return str(err)

class PreferenceCompanion(ExplorerNodes.ExplorerCompanion):
    def __init__(self, name, prefNode, ):
        ExplorerNodes.ExplorerCompanion.__init__(self, name)
        self.prefNode = prefNode

        self._breaks = {}

    typeMap = {}
    customTypeMap = {'filepath': PropertyEditors.FilepathConfPropEdit,
                     'dirpath': PropertyEditors.DirpathConfPropEdit,
                     'keydef': KeyDefConfPropEdit}
    def getPropEditor(self, prop):
        # XXX Using name equality to identify _breaks' prop edit is ugly !
        for aProp in self.propItems:
            if aProp[0] == prop: break
        else:
            raise Exception('Property "%s" not found'%prop)

        srcVal = aProp[1]
        opts = aProp[4]

        if prop in self._breaks.values():
            return None

        if opts:
            if opts[:2] == '##':
                return self.customTypeMap.get(string.strip(opts[2:]), None)
            else:
                return PropertyEditors.EnumConfPropEdit

        if string.lower(srcVal) in ('true', 'false'):
            return PropertyEditors.BoolConfPropEdit

        try:
            val = eval(srcVal, vars(Preferences))
        except Exception, error:
            return PropertyEditors.StrConfPropEdit

        if isinstance(val, wx.wxColour):
            return PropertyEditors.ColourConfPropEdit
        return self.typeMap.get(type(val), PropertyEditors.StrConfPropEdit)

    def getPropertyHelp(self, propName):
        for prop in self.propItems:
            if prop[0] == propName: return prop[3]
        else:
            return propName

    def getPropertyItems(self):
        order, vals, props, comments, options, self._breaks = self.prefNode.load()

        # remove empty break lines (-----------------------)
        for lineNo in self._breaks.keys():
            if not self._breaks[lineNo]:
                del self._breaks[lineNo]

        breakLinenos = self._breaks.keys()
        breakLinenos.sort()
        if len(breakLinenos):
            breaksIdx = 0
        else:
            breaksIdx = None

        res = []
        for name, value, comment, option in map(None, order, vals, comments, options):
            if breaksIdx is not None and \
                  props[name].start > breakLinenos[breaksIdx]:
                res.append( (self._breaks[breakLinenos[breaksIdx]], '', None, '', '') )
                if breaksIdx == len(self._breaks) -1:
                    breaksIdx = None
                else:
                    breaksIdx = breaksIdx + 1
            res.append( (name, value, props[name], comment, option) )
        return res

    def setPropHook(self, name, value, oldProp):
        # XXX validate etc.
        try:
            eval(value, vars(Preferences))
        except Exception, error:
            wx.wxLogError('Error: '+str(error))
            return false
        else:
            newProp = (name, value) + oldProp[2:]
            self.prefNode.save(name, newProp)
            return true

    def persistedPropVal(self, name, setterName):
        if name in self._breaks.values():
            return 'PROP_CATEGORY'
        else:
            return None

    def getPropOptions(self, name):
        for prop in self.propItems:
            if prop[0] == name:
                strOpts = prop[4]
                if strOpts and strOpts[:2] != '##':
                    return self.eval(strOpts)
                else:
                    return ()
        else:
            return ()

    def getPropNames(self, name):
        for prop in self.propItems:
            if prop[0] == name:
                strOpts = prop[4]
                if strOpts and strOpts[:2] != '##':
                    return methodparse.safesplitfields(strOpts, ',')
                else: return ()
        else:
            return ()

    def eval(self, expr):
        import PaletteMapping
        return PaletteMapping.evalCtrl(expr, vars(Preferences))

##    def GetProp(self, name):
##        ExplorerNodes.ExplorerCompanion.GetProp(self, name)
##        return self.findProp(name)[0][1]

class CorePluginsGroupNode(PreferenceGroupNode):
    """ """
    protocol = 'prefs.group.plug-in.core'
    defName = 'CorePluginPrefsGroup'
    def __init__(self):
        name = 'Core support'
        PreferenceGroupNode.__init__(self, name, None)

        self.vetoSort = true
        self.preferences = []

    def isFolderish(self):
        return true

    def openList(self):
        return self.preferences

    def notifyBeginLabelEdit(self, event):
        event.Veto()

class PluginFileExplNode(ExplorerNodes.ExplorerNode):
    """  """
    def __init__(self, name, enabled, status, resourcepath, imgIdx):
        ExplorerNodes.ExplorerNode.__init__(self, name, resourcepath, None,
              imgIdx, None, {})
        self.pluginEnabled = enabled
        self.pluginStatus = status

    def open(self, editor):
        """  """
        if self.pluginEnabled:
            msg = 'Disable'
        else:
            msg = 'Enable'

        if wx.wxMessageBox('%s %s?'%(msg, self.name), 'Confirm Toggle Plug-in',
              wx.wxYES_NO | wx.wxICON_QUESTION) == wx.wxYES:
            initPluginPath = os.path.dirname(self.resourcepath)
            initPluginGlobals = Utils.readInitPluginGlobals(initPluginPath)

            if self.pluginEnabled:
                initPluginGlobals['__disabled__'].append(self.name)
            else:
                try:
                    initPluginGlobals['__disabled__'].remove(self.name)
                except ValueError:
                    pass

            Utils.writeInitPluginGlobals(initPluginPath, initPluginGlobals)

            editor.explorer.list.refreshCurrent()

        return None, None

    def getURI(self):
        return '%s (%s)'%(ExplorerNodes.ExplorerNode.getURI(self),
                          self.pluginStatus)

    def isFolderish(self):
        return false

    def notifyBeginLabelEdit(self, event):
        event.Veto()

    def changeOrder(self, direction):
        initPluginPath = os.path.dirname(self.resourcepath)
        initPluginGlobals = Utils.readInitPluginGlobals(initPluginPath)
        ordered = initPluginGlobals['__ordered__']
        try:
            idx = ordered.index(self.name)
        except ValueError:
            idx = len(ordered)+1
        else:
            del ordered[idx]
        idx = max(idx + direction, 0)
        if idx <= len(ordered):
            ordered.insert(idx, self.name)
        Utils.writeInitPluginGlobals(initPluginPath, initPluginGlobals)


class PluginFilesGroupNode(PreferenceGroupNode):
    """ Represents a group of preference collections """
    protocol = 'prefs.group.plug-in.files'
    defName = 'PluginFilesPrefsGroup'
    def __init__(self):
        name = 'Plug-in files'
        PreferenceGroupNode.__init__(self, name, None)

    def openList(self):
        res = []
        splitext = os.path.splitext
        for filename, ordered, enabled in Utils.buildPluginExecList():
            if os.path.basename(filename) == '__init__.plug-in.py':
                continue
##
##                for path in Preferences.pluginPaths:
##            for filename in glob.glob('%s/*plug-in*.py'%path):
##            enabled = filename[-19:] != 'plug-in.disabled.py'
            name = splitext(splitext(os.path.basename(filename))[0])[0]
            if not enabled:
                name = splitext(name)[0]
                status = 'Disabled'
                imgIdx = EditorHelper.imgSystemObjDisabled
            else:
                fn = string.lower(filename)
                if Preferences.failedPlugins.has_key(fn):
                    kind, msg = Preferences.failedPlugins[fn]
                    if kind == 'Skipped':
                        status = 'Skipped plug-in: %s'% msg
                        imgIdx = EditorHelper.imgSystemObjPending
                    else:
                        status = 'Broken plug-in: %s'% msg
                        imgIdx = EditorHelper.imgSystemObjBroken
                elif fn in Preferences.installedPlugins:
                    if ordered:
                        status = 'Installed, ordered'
                        imgIdx = EditorHelper.imgSystemObjOrdered
                    else:
                        status = 'Installed'
                        imgIdx = EditorHelper.imgSystemObj
                else:
                    status = 'Pending restart'
                    imgIdx = EditorHelper.imgSystemObjPending

            res.append(PluginFileExplNode(name, enabled, status, filename, imgIdx))
        return res


class PluginFilesGroupNodeController(ExplorerNodes.Controller):
    moveUpBmp = 'Images/Shared/up.png'
    moveDownBmp = 'Images/Shared/down.png'

    itemDescr = 'item'

    def __init__(self, editor, list, inspector, controllers):
        ExplorerNodes.Controller.__init__(self, editor)
        self.list = list
        self.menu = wx.wxMenu()

        [wxID_PF_TOGGLE, wxID_PF_OPEN, wxID_PF_UP, wxID_PF_DOWN] = Utils.wxNewIds(4)

        self.transpMenuDef = ( (wxID_PF_TOGGLE, 'Toggle Enable/Disabled',
                                self.OnToggleState, '-'),
                               (wxID_PF_OPEN, 'Open plug-in file',
                                self.OnOpenPlugin, '-'),
                               (-1, '-', None, ''),
                               (wxID_PF_UP, 'Move up',
                                self.OnMovePluginUp, self.moveUpBmp),
                               (wxID_PF_DOWN, 'Move down',
                                self.OnMovePluginDown, self.moveDownBmp),
                               )

        self.setupMenu(self.menu, self.list, self.transpMenuDef)
        self.toolbarMenus = [self.transpMenuDef]

    def destroy(self):
        self.transpMenuDef = ()
        self.toolbarMenus = ()
        self.menu.Destroy()

    def OnToggleState(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            for node in nodes:
                node.open(self.editor)

    def OnOpenPlugin(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            for node in nodes:
                self.editor.openOrGotoModule(node.resourcepath)

    def OnMovePluginUp(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            if len(nodes) != 1:
                wx.wxLogError('Can only move 1 at a time')
            else:
                node = nodes[0]
                idx = self.list.items.index(node)
                if idx == 0:
                    wx.wxLogError('Already at the beginning')
                else:
                    name = node.name
                    node.changeOrder(-1)
                    self.list.refreshCurrent()
                    self.list.selectItemNamed(name)

    def OnMovePluginDown(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            if len(nodes) != 1:
                wx.wxLogError('Can only move 1 at a time')
            else:
                node = nodes[0]
                idx = self.list.items.index(node)
##                if idx >= len(self.list.items) -1:
##                    wx.wxLogError('Already at the end')
##                else:
                name = node.name
                node.changeOrder(1)
                self.list.refreshCurrent()
                self.list.selectItemNamed(name)



class TransportPluginExplNode(ExplorerNodes.ExplorerNode):
    """  """
    protocol = 'transport'
    def __init__(self, name, status, imgIdx):
        ExplorerNodes.ExplorerNode.__init__(self, name, '%s (%s)'%(name, status),
              None, imgIdx, None, {})
        self.status = status


    def open(self, editor):
        return None, None

class TransportPluginsController(ExplorerNodes.Controller):
    addItemBmp = 'Images/Shared/NewItem.png'
    removeItemBmp = 'Images/Shared/DeleteItem.png'
    moveUpBmp = 'Images/Shared/up.png'
    moveDownBmp = 'Images/Shared/down.png'

    itemDescr = 'item'

    def __init__(self, editor, list, inspector, controllers):
        ExplorerNodes.Controller.__init__(self, editor)
        self.list = list
        self.menu = wx.wxMenu()

        [wxID_TP_NEW, wxID_TP_DEL, wxID_TP_UP, wxID_TP_DOWN] = Utils.wxNewIds(4)

        self.transpMenuDef = ( (wxID_TP_NEW, 'Add new '+self.itemDescr,
                                self.OnNewTransport, self.addItemBmp),
                               (wxID_TP_DEL, 'Remove '+self.itemDescr,
                                self.OnDeleteTransport, self.removeItemBmp),
                               (-1, '-', None, ''),
                               (wxID_TP_UP, 'Move up',
                                self.OnMoveTransportUp, self.moveUpBmp),
                               (wxID_TP_DOWN, 'Move down',
                                self.OnMoveTransportDown, self.moveDownBmp),
                               )

        self.setupMenu(self.menu, self.list, self.transpMenuDef)
        self.toolbarMenus = [self.transpMenuDef]

    def destroy(self):
        self.transpMenuDef = ()
        self.toolbarMenus = ()
        self.menu.Destroy()

    def editorUpdateNotify(self, info=''):
        self.OnReloadItems()

    def OnReloadItems(self, event=None):
        if self.list.node:
            self.list.refreshCurrent()

    def moveTransport(self, node, idx, direc):
        names = []
        for item in self.list.items:
            names.append(item.name)

        name = names[idx]
        del names[idx]
        names.insert(idx + direc, name)

        self.list.node.updateOrder(names)

        self.list.refreshCurrent()
        self.list.selectItemByIdx(idx+direc+1)

    def OnMoveTransportUp(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            if len(nodes) != 1:
                wx.wxLogError('Can only move 1 at a time')
            else:
                node = nodes[0]
                idx = self.list.items.index(node)
                if idx == 0:
                    wx.wxLogError('Already at the beginning')
                else:
                    self.moveTransport(node, idx, -1)

    def OnMoveTransportDown(self, event):
        if self.list.node:
            ms = self.list.getMultiSelection()
            nodes = self.getNodesForSelection(ms)
            if len(nodes) != 1:
                wx.wxLogError('Can only move 1 at a time')
            else:
                node = nodes[0]
                idx = self.list.items.index(node)
                if idx >= len(self.list.items) -1:
                    wx.wxLogError('Already at the end')
                else:
                    self.moveTransport(node, idx, 1)

    def OnNewTransport(self, event):
        pass

    def OnDeleteTransport(self, event):
        pass

class TransportPluginsLoadOrderController(TransportPluginsController):
    itemDescr = 'Transport module'

    def OnNewTransport(self, event):
        dlg = wx.wxTextEntryDialog(self.list, 'Enter the fully qualified Python '\
               'object path to \nthe Transport module. E.g. Explorers.FileExplorer',
               'New Transport', '')
        try:
            if dlg.ShowModal() != wx.wxID_OK:
                return
            transportModulePath = dlg.GetValue()
        finally:
            dlg.Destroy()

        if not self.list.node.checkValidModulePath(transportModulePath):
            if wx.wxMessageBox('Cannot locate the specified module path,\n'\
                         'are you sure you want to continue?',
                         'Module not found',
                         wx.wxYES_NO | wx.wxICON_EXCLAMATION) == wx.wxNO:
                return

        names = []
        for item in self.list.items:
            names.append(item.name)

        names.append(transportModulePath)

        self.list.node.updateOrder(names)

        self.list.refreshCurrent()

    def OnDeleteTransport(self, event):
        selNames = self.list.getMultiSelection()
        nodes = self.getNodesForSelection(selNames)

        names = []
        for item in self.list.items:
            names.append(item.name)

        for item in nodes:
            names.remove(item.name)

        self.list.node.updateOrder(names)

        self.list.refreshCurrent()

class TransportPluginsTreeDisplayOrderController(TransportPluginsController):
    itemDescr = 'Transports tree node'

    def OnNewTransport(self, event):
        dlg = wx.wxTextEntryDialog(self.list, 'Enter the protocol identifier. E.g. '\
               'ftp, ssh', 'New Transports Tree Node', '')
        try:
            if dlg.ShowModal() != wx.wxID_OK:
                return
            protocol = dlg.GetValue()
        finally:
            dlg.Destroy()

        names = []
        for item in self.list.items:
            names.append(item.name)

        names.append(protocol)

        self.list.node.updateOrder(names)
        self.list.node.checkConfigEntry(protocol)

        self.list.refreshCurrent()

    def OnDeleteTransport(self, event):
        selNames = self.list.getMultiSelection()
        nodes = self.getNodesForSelection(selNames)

        names = []
        for item in self.list.items:
            names.append(item.name)

        for item in nodes:
            names.remove(item.name)
            self.list.node.clearEmptyConfigEntry(item.name)

        self.list.node.updateOrder(names)

        self.list.refreshCurrent()


class TransportPluginsLoadOrderGroupNode(PreferenceGroupNode):
    """  """
    protocol = 'prefs.group.plug-in.transport.load-order'
    defName = 'TransportPluginsPrefsGroup'
    def __init__(self):
        name = 'Loading order'
        PreferenceGroupNode.__init__(self, name, None)

    def openList(self):
        conf = Utils.createAndReadConfig('Explorer')

        modules = eval(conf.get('explorer', 'installedtransports'), {})
        assert isinstance(modules, types.ListType)

        res = []
        for mod in modules:
            if mod in ExplorerNodes.installedModules:
                status = 'Installed'
                imgIdx = EditorHelper.imgSystemObjOrdered
            elif mod in ExplorerNodes.failedModules.keys():
                status = 'Broken: %s'%ExplorerNodes.failedModules[mod]
                imgIdx = EditorHelper.imgSystemObjBroken
            else:
                status = 'Pending restart'
                imgIdx = EditorHelper.imgSystemObjPending

            res.append(TransportPluginExplNode(mod, status, imgIdx))
        return res

    def updateOrder(self, newOrder):
        conf = Utils.createAndReadConfig('Explorer')
        conf.set('explorer', 'installedtransports', pprint.pformat(newOrder))
        Utils.writeConfig(conf)

    def checkValidModulePath(self, name):
        try:
            Utils.find_dotted_module(name)
        except ImportError, err:
            #print str(err)
            return false
        else:
            return true


class TransportPluginsTreeDisplayOrderGroupNode(PreferenceGroupNode):
    """  """
    protocol = 'prefs.group.plug-in.transport.tree-order'
    defName = 'TransportPluginsPrefsGroup'
    def __init__(self):
        name = 'Tree display order'
        PreferenceGroupNode.__init__(self, name, None)

    def openList(self):
        conf = Utils.createAndReadConfig('Explorer')

        treeOrder = eval(conf.get('explorer', 'transportstree'), {})
        assert isinstance(treeOrder, type([]))

        res = []
        for prot in treeOrder:
            if not ExplorerNodes.nodeRegByProt.has_key(prot):
                status = 'Protocol not installed'
                imgIdx = EditorHelper.imgSystemObjPending
            else:
                status = 'Installed'
                imgIdx = EditorHelper.imgSystemObjOrdered

            res.append(TransportPluginExplNode(prot, status, imgIdx))
        return res

    def updateOrder(self, newOrder):
        conf = Utils.createAndReadConfig('Explorer')
        conf.set('explorer', 'transportstree', pprint.pformat(newOrder))
        Utils.writeConfig(conf)

    def checkConfigEntry(self, protocol):
        conf = Utils.createAndReadConfig('Explorer')
        if not conf.has_option('explorer', protocol):
            conf.set('explorer', protocol, '{}')
        Utils.writeConfig(conf)

    def clearEmptyConfigEntry(self, protocol):
        conf = Utils.createAndReadConfig('Explorer')
        if conf.has_option('explorer', protocol) and \
              eval(string.strip(conf.get('explorer', protocol)), {}) == {}:
            conf.remove_option('explorer', protocol)
            Utils.writeConfig(conf)


#-------------------------------------------------------------------------------
ExplorerNodes.register(BoaPrefGroupNode)
ExplorerNodes.register(PluginFilesGroupNode,
      controller=PluginFilesGroupNodeController)
ExplorerNodes.register(TransportPluginsLoadOrderGroupNode,
      controller=TransportPluginsLoadOrderController)
ExplorerNodes.register(TransportPluginsTreeDisplayOrderGroupNode,
      controller=TransportPluginsTreeDisplayOrderController)
