/* 
Copyright 2011 Hardcoded Software (http://www.hardcoded.net)

This software is licensed under the "BSD" License as described in the "LICENSE" file, 
which should be included with this package. The terms are also available at 
http://www.hardcoded.net/licenses/bsd_license
*/

#import <Cocoa/Cocoa.h>
#import "MGPanel.h"
#import "MGTableView.h"
#import "MGSplitTable.h"
#import "PyTransactionPanel.h"

@class MGMainWindowController;

@interface MGTransactionInspector : MGPanel {
    IBOutlet NSTabView *tabView;
    IBOutlet NSTextField *dateField;
    IBOutlet NSTextField *descriptionField;
    IBOutlet NSTextField *payeeField;
    IBOutlet NSTextField *checknoField;
    IBOutlet NSTextField *notesField;
    IBOutlet MGTableView *splitTableView;
    IBOutlet NSButton *mctBalanceButton;
    
    MGSplitTable *splitTable;
}
- (id)initWithParent:(MGMainWindowController *)aParent;
- (PyTransactionPanel *)model;
/* Actions */
- (IBAction)addSplit:(id)sender;
- (IBAction)deleteSplit:(id)sender;
- (IBAction)mctBalance:(id)sender;
@end
