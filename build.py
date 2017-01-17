# Copyright 2016 Virgil Dupras
#
# This software is licensed under the "GPLv3" License as described in the "LICENSE" file,
# which should be included with this package. The terms are also available at
# http://www.gnu.org/licenses/gpl-3.0.html

import sys
import os
import os.path as op
import shutil
import glob
import compileall
from argparse import ArgumentParser
import platform

from setuptools import setup, Extension

from hscommon import sphinxgen
from hscommon.plat import ISOSX, ISLINUX, ISWINDOWS
from hscommon.build import (
    print_and_do, copy_packages, move_all, copy, hardlink, filereplace,
    add_to_pythonpath, copy_sysconfig_files_for_embed, build_cocoalib_xibless, OSXAppStructure,
    build_cocoa_ext, copy_embeddable_python_dylib, collect_stdlib_dependencies
)
from hscommon import loc
from hscommon.util import ensure_folder, modified_after, delete_files_with_pattern

def parse_args():
    parser = ArgumentParser()
    parser.add_argument(
        '--ui',
        help="Type of UI to build. 'qt' or 'cocoa'. Default is determined by your system."
    )
    parser.add_argument(
        '--dev', action='store_true', default=False,
        help="If this flag is set, will configure for dev builds."
    )
    parser.add_argument(
        '--clean', action='store_true', dest='clean',
        help="Clean build folder before building"
    )
    parser.add_argument(
        '--doc', action='store_true', dest='doc',
        help="Build only the help file"
    )
    parser.add_argument(
        '--loc', action='store_true', dest='loc',
        help="Build only localization"
    )
    parser.add_argument(
        '--updatepot', action='store_true', dest='updatepot',
        help="Generate .pot files from source code."
    )
    parser.add_argument(
        '--mergepot', action='store_true', dest='mergepot',
        help="Update all .po files based on .pot files."
    )
    parser.add_argument(
        '--cocoamod', action='store_true', dest='cocoamod',
        help="Build only Cocoa modules"
    )
    parser.add_argument(
        '--ext', action='store_true', dest='ext',
        help="Build only ext modules"
    )
    parser.add_argument(
        '--no-ext', action='store_true', dest='no_ext',
        help="Do not build ext modules."
    )
    parser.add_argument(
        '--cocoa-compile', action='store_true', dest='cocoa_compile',
        help="Build only Cocoa executable"
    )
    parser.add_argument(
        '--xibless', action='store_true', dest='xibless',
        help="Build only xibless UIs"
    )
    parser.add_argument(
        '--normpo', action='store_true', dest='normpo',
        help="Normalize all PO files (do this before commit)."
    )
    args = parser.parse_args()
    return args

def clean():
    TOCLEAN = [
        'build',
        op.join('cocoa', 'build'),
        op.join('cocoa', 'autogen'),
        'dist',
        'install',
        op.join('help', 'en', 'image')
    ]
    for path in TOCLEAN:
        try:
            os.remove(path)
        except Exception:
            try:
                shutil.rmtree(path)
            except Exception:
                pass

def cocoa_compile_command():
    return '{0} waf configure && {0} waf'.format(sys.executable)

def cocoa_app():
    return OSXAppStructure('build/moneyGuru.app')

def build_xibless(dest='cocoa/autogen'):
    import xibless
    ensure_folder(dest)
    FNPAIRS = [
        ('lookup.py', 'MGLookup_UI'),
        ('schedule_scope_dialog.py', 'MGRecurrenceScopeDialog_UI'),
        ('custom_date_range_dialog.py', 'MGCustomDateRangePanel_UI'),
        ('account_reassign_panel.py', 'MGAccountReassignPanel_UI'),
        ('csv_layout_name.py', 'MGCSVLayoutNameDialog_UI'),
        ('csv_import_options.py', 'MGCSVImportOptions_UI'),
        ('import_window.py', 'MGImportWindow_UI'),
        ('export_panel.py', 'MGExportPanel_UI'),
        ('budget_panel.py', 'MGBudgetPanel_UI'),
        ('schedule_panel.py', 'MGSchedulePanel_UI'),
        ('mass_editing_panel.py', 'MGMassEditionPanel_UI'),
        ('transaction_panel.py', 'MGTransactionInspector_UI'),
        ('account_panel.py', 'MGAccountProperties_UI'),
        ('newtab_view.py', 'MGEmptyView_UI'),
        ('docprops_view.py', 'MGDocPropsView_UI'),
        ('transaction_view.py', 'MGTransactionView_UI'),
        ('account_view.py', 'MGAccountView_UI'),
        ('account_sheet_view.py', 'MGAccountSheetView_UI'),
        ('date_range_selector.py', 'MGDateRangeSelector_UI'),
        ('main_window.py', 'MGMainWindowController_UI'),
        ('preferences_panel.py', 'MGPreferencesPanel_UI'),
        ('main_menu.py', 'MGMainMenu_UI'),
    ]
    for srcname, dstname in FNPAIRS:
        srcpath = op.join('cocoa', 'ui', srcname)
        dstpath = op.join(dest, dstname)
        if modified_after(srcpath, dstpath + '.h'):
            print("Generating xibless UI %s" % srcpath)
            xibless.generate(srcpath, dstpath, localizationTable='Localizable')

def build_cocoa(dev):
    print("Creating OS X app structure")
    app = cocoa_app()
    # We import this here because we don't want opened module to prevent us replacing .pyd files.
    from core.app import Application as MoneyGuruApp
    app_version = MoneyGuruApp.VERSION
    filereplace('cocoa/InfoTemplate.plist', 'build/Info.plist', version=app_version)
    app.create('build/Info.plist')
    print("Building localizations")
    build_localizations('cocoa')
    print("Building xibless UIs")
    build_cocoalib_xibless()
    build_xibless()
    print("Building Python extensions")
    build_cocoa_proxy_module()
    build_cocoa_bridging_interfaces()
    print("Building the cocoa layer")
    copy_embeddable_python_dylib('build')
    pydep_folder = op.join(app.resources, 'py')
    ensure_folder(pydep_folder)
    if dev:
        hardlink('cocoa/mg_cocoa.py', 'build/mg_cocoa.py')
    else:
        copy('cocoa/mg_cocoa.py', 'build/mg_cocoa.py')
    tocopy = ['core', 'hscommon', 'cocoalib/cocoa', 'objp', 'yahoo_finance', 'simplejson', 'pytz']
    copy_packages(tocopy, pydep_folder, create_links=dev)
    sys.path.insert(0, 'build')
    collect_stdlib_dependencies('build/mg_cocoa.py', pydep_folder)
    del sys.path[0]
    copy_sysconfig_files_for_embed(pydep_folder)
    if not dev:
        # Important: Don't ever run delete_files_with_pattern('*.py') on dev builds because you'll
        # be deleting all py files in symlinked folders.
        compileall.compile_dir(pydep_folder, force=True, legacy=True)
        delete_files_with_pattern(pydep_folder, '*.py')
        delete_files_with_pattern(pydep_folder, '__pycache__')
    print("Compiling with WAF")
    os.chdir('cocoa')
    print_and_do(cocoa_compile_command())
    os.chdir('..')
    app.copy_executable('cocoa/build/moneyGuru')
    build_help()
    print("Copying resources and frameworks")
    resources = [
        'cocoa/dsa_pub.pem', 'build/mg_cocoa.py', 'build/help', 'data/example.moneyguru',
    ] + glob.glob('images/*')
    app.copy_resources(*resources, use_symlinks=dev)
    app.copy_frameworks(
        'build/Python', 'cocoalib/Sparkle.framework',
    )
    print("Creating the run.py file")
    tmpl = open('run_template_cocoa.py', 'rt').read()
    run_contents = tmpl.replace('{{app_path}}', app.dest)
    open('run.py', 'wt').write(run_contents)

def build_qt(dev):
    qrc_path = op.join('qt', 'mg.qrc')
    pyrc_path = op.join('qt', 'mg_rc.py')
    ret = print_and_do("pyrcc5 {} > {}".format(qrc_path, pyrc_path))
    if ret != 0:
        raise RuntimeError("pyrcc5 call failed with code {}. Aborting build".format(ret))
    build_help()
    print("Creating the run.py file")
    shutil.copy('run_template_qt.py', 'run.py')

def build_help():
    print("Generating Help")
    current_platform = 'osx' if ISOSX else 'win'
    current_path = op.abspath('.')
    confpath = op.join(current_path, 'help', 'conf.tmpl')
    help_basepath = op.join(current_path, 'help', 'en')
    help_destpath = op.join(current_path, 'build', 'help')
    changelog_path = op.join(current_path, 'help', 'changelog')
    credits_path = op.join(current_path, 'help', 'credits.rst')
    credits_tmpl = op.join(help_basepath, 'credits.tmpl')
    credits_out = op.join(help_basepath, 'credits.rst')
    filereplace(credits_tmpl, credits_out, credits=open(credits_path, 'rt', encoding='utf-8').read())
    image_src = op.join(current_path, 'help', 'image_{}'.format(current_platform))
    image_dst = op.join(current_path, 'help', 'en', 'image')
    if not op.exists(image_dst):
        try:
            os.symlink(image_src, image_dst)
        except (NotImplementedError, OSError): # Windows crappy symlink support
            shutil.copytree(image_src, image_dst)
    tixurl = "https://github.com/hsoft/moneyguru/issues/{}"
    confrepl = {'platform': current_platform}
    sphinxgen.gen(help_basepath, help_destpath, changelog_path, tixurl, confrepl, confpath)

def build_base_localizations():
    loc.compile_all_po('locale')

def build_qt_localizations():
    loc.compile_all_po(op.join('qtlib', 'locale'))
    loc.merge_locale_dir(op.join('qtlib', 'locale'), 'locale')

def build_localizations(ui):
    build_base_localizations()
    if ui == 'cocoa':
        app = cocoa_app()
        loc.build_cocoa_localizations(app)
        locale_dest = op.join(app.resources, 'locale')
    elif ui == 'qt':
        build_qt_localizations()
        locale_dest = op.join('build', 'locale')
    if op.exists(locale_dest):
        shutil.rmtree(locale_dest)
    shutil.copytree('locale', locale_dest, ignore=shutil.ignore_patterns('*.po', '*.pot'))
    if ui == 'qt' and not ISLINUX:
        print("Copying qt_*.qm files into the 'locale' folder")
        from PyQt5.QtCore import QLibraryInfo
        trfolder = QLibraryInfo.location(QLibraryInfo.TranslationsPath)
        for lang in loc.get_langs('locale'):
            qmname = 'qt_%s.qm' % lang
            src = op.join(trfolder, qmname)
            if op.exists(src):
                copy(src, op.join('build', 'locale', qmname))

def build_updatepot():
    if ISOSX:
        print("Updating Cocoa strings file.")
        build_cocoalib_xibless('cocoalib/autogen')
        loc.generate_cocoa_strings_from_code('cocoalib', 'cocoalib/en.lproj')
        # If we don't delete 'cocoalib/autogen', it messes with compilation
        shutil.rmtree('cocoalib/autogen')
        build_xibless()
        loc.generate_cocoa_strings_from_code('cocoa', 'cocoa/en.lproj')
    print("Building .pot files from source files")
    print("Building core.pot")
    loc.generate_pot(['core'], op.join('locale', 'core.pot'), ['tr'])
    print("Building columns.pot")
    loc.generate_pot(['core'], op.join('locale', 'columns.pot'), ['trcol'])
    print("Building ui.pot")
    # When we're not under OS X, we don't want to overwrite ui.pot because it contains Cocoa locs
    # We want to merge the generated pot with the old pot in the most preserving way possible.
    loc.generate_pot(['qt'], op.join('locale', 'ui.pot'), ['tr'], merge=(not ISOSX))
    print("Building qtlib.pot")
    loc.generate_pot(['qtlib'], op.join('qtlib', 'locale', 'qtlib.pot'), ['tr'])
    if ISOSX:
        print("Building cocoalib.pot")
        cocoalib_pot = op.join('cocoalib', 'locale', 'cocoalib.pot')
        os.remove(cocoalib_pot)
        loc.strings2pot(op.join('cocoalib', 'en.lproj', 'cocoalib.strings'), cocoalib_pot)
        print("Enhancing ui.pot with Cocoa's strings files")
        loc.strings2pot(op.join('cocoa', 'en.lproj', 'Localizable.strings'), op.join('locale', 'ui.pot'))

def build_mergepot():
    print("Updating .po files using .pot files")
    loc.merge_pots_into_pos('locale')
    loc.merge_pots_into_pos(op.join('qtlib', 'locale'))

def build_normpo():
    loc.normalize_all_pos('locale')
    loc.normalize_all_pos(op.join('qtlib', 'locale'))
    loc.normalize_all_pos(op.join('cocoalib', 'locale'))

def build_ext():
    print("Building C extensions")
    if ISWINDOWS and platform.architecture()[0] == '64bit':
        print("""Detecting a 64bit Windows here. You might have problems compiling. If you do, do this:
1. Install the Windows SDK.
2. Start the Windows SDK's console.
3. Then run:
setenv /x64 /release
set DISTUTILS_USE_SDK=1
set MSSdk=1
4. Try the build command again.
If the above fails and you are testing locally for a non-production release,
then you can pass a --no-ext option to this build script to skip the extension
module which will then use pure python reference implementations.
        """)
    exts = []
    exts.append(Extension(
        '_amount',
        [op.join('core', 'modules', 'amount.c')],
        # Needed to avoid tricky compile warnings after having enabled the strict ABI
        extra_compile_args=['-fno-strict-aliasing'],
    ))
    setup(
        script_args=['build_ext', '--inplace'],
        ext_modules=exts,
    )
    move_all('_amount*', op.join('core', 'model'))

def build_cocoa_proxy_module():
    print("Building Cocoa Proxy")
    import objp.p2o
    objp.p2o.generate_python_proxy_code('cocoalib/cocoa/CocoaProxy.h', 'build/CocoaProxy.m')
    build_cocoa_ext(
        "CocoaProxy", 'cocoalib/cocoa',
        ['cocoalib/cocoa/CocoaProxy.m', 'build/CocoaProxy.m', 'build/ObjP.m',
            'cocoalib/HSErrorReportWindow.m', 'cocoa/autogen/HSErrorReportWindow_UI.m'],
        ['AppKit', 'CoreServices'],
        ['cocoalib', 'cocoa/autogen']
    )

def build_cocoa_bridging_interfaces():
    print("Building Cocoa Bridging Interfaces")
    import objp.o2p
    import objp.p2o
    import objp.const
    add_to_pythonpath('cocoa')
    add_to_pythonpath('cocoalib')
    from cocoa.inter import (
        PyGUIObject, GUIObjectView, PyTextField, PyTable, TableView, PyColumns,
        ColumnsView, PyOutline, PySelectableList, SelectableListView, PyBaseApp, BaseAppView
    )
    # This createPool() business is a bit hacky, but upon importing mg_cocoa, we call
    # install_gettext_trans_under_cocoa() which uses proxy functions (and thus need an active
    # autorelease pool). If we don't do that, we get leak warnings.
    from cocoa import proxy
    proxy.createPool()
    from mg_cocoa import (
        PyPanel, PanelView, PyBaseView,
        PyTableWithDate, PyCompletableEdit, PyDateWidget,
        PyCSVImportOptions, CSVImportOptionsView, PyImportTable, PySplitTable, PyLookup, LookupView,
        PyDateRangeSelector, DateRangeSelectorView, PyImportWindow, ImportWindowView,
        PyFilterBar, FilterBarView, PyReport, ReportView, PyScheduleTable, PyBudgetTable,
        PyEntryTable, PyTransactionTable, PyGeneralLedgerTable, PyChart, ChartView,
        PyAccountPanel, PyMassEditionPanel, PyBudgetPanel, BudgetPanelView, PyCustomDateRangePanel,
        PyAccountReassignPanel, PyExportPanel, ExportPanelView, PyPanelWithTransaction,
        PanelWithTransactionView, PyTransactionPanel, PySchedulePanel, SchedulePanelView,
        BaseViewView, PyAccountSheetView, PyTransactionView,
        PyAccountView, AccountViewView, PyScheduleView, PyBudgetView,
        PyGeneralLedgerView, PyDocPropsView, PyPluginListView, PyEmptyView, PyReadOnlyPluginView,
        PyMainWindow, MainWindowView, PyDocument, DocumentView, PyMoneyGuruApp
    )
    from mg_cocoa import PyPrintView, PySplitPrint, PyTransactionPrint, PyEntryPrint
    allclasses = [
        PyGUIObject, PyTextField, PyTable, PyColumns, PyOutline, PySelectableList,
        PyBaseApp, PyPanel, PyBaseView, PyTableWithDate, PyCompletableEdit, PyDateWidget,
        PyCSVImportOptions, PyImportTable, PySplitTable, PyLookup, PyDateRangeSelector,
        PyImportWindow, PyFilterBar, PyReport, PyScheduleTable, PyBudgetTable,
        PyEntryTable, PyTransactionTable, PyGeneralLedgerTable, PyChart, PyAccountPanel,
        PyMassEditionPanel, PyBudgetPanel, PyCustomDateRangePanel, PyAccountReassignPanel,
        PyExportPanel, PyPanelWithTransaction, PyTransactionPanel, PySchedulePanel,
        PyAccountSheetView, PyTransactionView, PyAccountView, PyScheduleView, PyBudgetView,
        PyGeneralLedgerView, PyDocPropsView, PyPluginListView, PyEmptyView, PyReadOnlyPluginView,
        PyMainWindow, PyDocument, PyMoneyGuruApp
    ]
    proxy.destroyPool()
    allclasses += [PyPrintView, PySplitPrint, PyTransactionPrint, PyEntryPrint]
    for class_ in allclasses:
        objp.o2p.generate_objc_code(class_, 'cocoa/autogen', inherit=True)
    allclasses = [
        GUIObjectView, TableView, ColumnsView, SelectableListView, BaseAppView,
        PanelView, CSVImportOptionsView, LookupView, DateRangeSelectorView, ImportWindowView,
        FilterBarView, ReportView, BudgetPanelView, ExportPanelView, PanelWithTransactionView,
        SchedulePanelView, BaseViewView, AccountViewView, MainWindowView,
        DocumentView, ChartView
    ]
    clsspecs = [objp.o2p.spec_from_python_class(class_) for class_ in allclasses]
    objp.p2o.generate_python_proxy_code_from_clsspec(clsspecs, 'build/CocoaViews.m')
    py_folder = op.join(cocoa_app().resources, 'py')
    ensure_folder(py_folder)
    build_cocoa_ext('CocoaViews', py_folder, ['build/CocoaViews.m', 'build/ObjP.m'])
    import mg_const
    objp.const.generate_objc_code(mg_const, 'cocoa/autogen/PyConst.h')

def build_normal(ui, dev, do_build_ext=True):
    build_localizations(ui)
    if do_build_ext:
        build_ext()
    if ui == 'cocoa':
        build_cocoa(dev)
    elif ui == 'qt':
        build_qt(dev)

def main():
    args = parse_args()
    ui = args.ui
    if ui not in ('cocoa', 'qt'):
        ui = 'cocoa' if ISOSX else 'qt'
    print("Building moneyGuru with UI {}".format(ui))
    if args.dev:
        print("Building in Dev mode")
    if args.clean:
        clean()
    if not op.exists('build'):
        os.mkdir('build')
    if args.doc:
        build_help()
    elif args.loc:
        build_localizations(ui)
    elif args.updatepot:
        build_updatepot()
    elif args.mergepot:
        build_mergepot()
    elif args.normpo:
        build_normpo()
    elif args.cocoamod:
        build_cocoa_proxy_module()
        build_cocoa_bridging_interfaces()
    elif args.ext:
        build_ext()
    elif args.cocoa_compile:
        os.chdir('cocoa')
        print_and_do(cocoa_compile_command())
        os.chdir('..')
        cocoa_app().copy_executable('cocoa/build/moneyGuru')
    elif args.xibless:
        build_cocoalib_xibless()
        build_xibless()
    else:
        build_normal(ui, args.dev, not args.no_ext)

if __name__ == '__main__':
    main()

