#!/bin/env python
import os, sys, re
from xml.dom.minidom import parseString
from optparse import OptionParser

# parse args
parser = OptionParser("""%prog <genicam_xml> <camera_name>

This script parses a genicam xml file and creates a database template and edm 
screen to go with it. The edm screen should be used as indication of what
the driver supports, and the generated summary screen should be edited to make
a more sensible summary. The Db file will be generated in:
  ../Db/<camera_name>.template
and the edm files will be called:
  ../op/edl/<camera_name>.edl
  ../op/edl/<camera_name>-features.edl""")
parser.add_option("", "--devInt64",
                  action="store_true", dest="devInt64", default=False,
                  help="use int64in and int64out records. Requires at least EPICS base 3.16.1 or EPICS 7.")
options, args = parser.parse_args()
if len(args) != 2:
    parser.error("Incorrect number of arguments")
if (options.devInt64):
  GCIntegerInputRecordType = "int64in"
  GCIntegerOutputRecordType = "int64out"
else:
  GCIntegerInputRecordType = "ai"
  GCIntegerOutputRecordType = "ao"

# Check the first two lines of the feature xml file to see if arv-tool left
# the camera id there, thus creating an unparsable file
# Throw it away if it doesn't look like valid xml
# A valid first line of an xml file will be optional whitespace followed by '<'
genicam_lines = open(args[0]).readlines()
try:
    start_line = min(i for i in range(2) if genicam_lines[i].lstrip().startswith("<"))
except:
    print "Neither of these lines looks like valid XML:"
    print "".join(genicam_lines[:2])
    sys.exit(1)

xml_root = parseString("".join(genicam_lines[start_line:]).lstrip())

camera_name = args[1]
prefix = os.path.abspath(os.path.join(os.path.dirname(__file__),".."))
db_filename = os.path.join(prefix, "Db", camera_name + ".template")
edl_filename = os.path.join(prefix, "op", "edl", camera_name + ".edl")
edl_more_filename = os.path.join(prefix, "op", "edl", camera_name + "-features.edl")

# function to read element children of a node
def elements(node):
    return [n for n in node.childNodes if n.nodeType == n.ELEMENT_NODE]  

# a function to read the text children of a node
def getText(node):
    return ''.join([n.data for n in node.childNodes if n.nodeType == n.TEXT_NODE])

# node lookup from nodeName -> node
lookup = {}
# lookup from nodeName -> recordName
records = {}
categories = []

# function to create a lookup table of nodes
def handle_node(node):
    if node.nodeName == "Group":
        for n in elements(node):
            handle_node(n)
    elif node.hasAttribute("Name"):
        name = str(node.getAttribute("Name"))
        lookup[name] = node
        # Add a leading GC_ to the name to prevent identical record names to those in ADBase.template
        recordName = "GC_" + name
        if len(recordName) > 20:
            words=re.findall('[a-zA-Z][^A-Z]*', recordName)
            for i in range(len(words)):
                word = words[i]
                if (len(word) > 3):
                    word = word[:3]
                    words[i] = word
                    s = ''
                    recordName = s.join(words)
                    if (len(recordName) <= 20): break
        if len(recordName) > 20:
            recordName = recordName[:20]
        i = 0
        while recordName in records.values():
            recordName = recordName[:-len(str(i))] + str(i)
            i += 1
        records[name] = recordName
        if node.nodeName == "Category":
            categories.append(name)
    elif node.nodeName != "StructReg":
        print "Node has no Name attribute", node

# list of all nodes    
for node in elements(elements(xml_root)[0]):
    handle_node(node)

# Now make structure, [(title, [features...]), ...]
structure = []
doneNodes = []
def handle_category(category):
    # making flat structure, so if its already there then don't do anything
    if category in [x[0] for x in structure]:
        return
    node = lookup[category]
    # for each child feature of this node
    features = []
    cgs = []
    for feature in elements(node):        
        if feature.nodeName == "pFeature":
            featureName = str(getText(feature))
            featureNode = lookup[featureName]
            if str(featureNode.nodeName) == "Category":
                cgs.append(featureName)
            else:
                if featureNode not in doneNodes:
                    features.append(featureNode)   
                    doneNodes.append(featureNode)
    if features:
        if len(features) > 32:
            i = 1
            while features:
                structure.append((category+str(i), features[:32]))
                i += 1
                features = features[32:]
        else:            
            structure.append((category, features))
    for category in cgs:
        handle_category(category)

for category in categories:
    handle_category(category)
    
# Spit out a database file
db_file = open(db_filename, "w")
stdout = sys.stdout
sys.stdout = db_file

# print a header
print '# Macros:'
print '#% macro, P, Device Prefix'
print '#% macro, R, Device Suffix'
print '#% macro, PORT, Asyn Port name'
print '#% macro, TIMEOUT, Timeout, default=1'
print '#% macro, ADDR, Asyn Port address, default=0'
print '#%% gui, $(PORT), edmtab, %s.edl, P=$(P),R=$(R)' % camera_name
print 

a_autosaveFields		= 'DESC LOLO LOW HIGH HIHI LLSV LSV HSV HHSV EGU TSE PREC'
b_autosaveFields		= 'DESC ZSV OSV TSE'
long_autosaveFields		= 'DESC LOLO LOW HIGH HIHI LLSV LSV HSV HHSV EGU TSE'
mbb_autosaveFields		= 'DESC ZRSV ONSV TWSV THSV FRSV FVSV SXSV SVSV EISV NISV TESV ELSV TVSV TTSV FTSV FFSV TSE'
string_autosaveFields	        = 'DESC TSE'

# Create CamModel and CamType related PV's for navigation and labeling
print 'record(stringin, "$(P)$(R)CamModel") {'
print '  field(VAL,   "%s")' % camera_name
print '  field(PINI,  "YES")'
print '}'
print
print 'record(stringin, "$(P)$(R)CamModelScreen") {'
print '  field(VAL,   "vimbaScreens/%s")' % camera_name
print '  field(PINI,  "YES")'
print '}'
print
print 'record(stringin, "$(P)$(R)CamType") {'
print '  field(VAL,   "$(TYPE=vimba)")'
print '  field(PINI,  "YES")'
print '}'
print
print 'record(stringin, "$(P)$(R)CamTypeScreen") {'
print '  field(VAL,   "vimbaScreens/$(TYPE=vimba)CamType.edl")'
print '  field(PINI,  "YES")'
print '}'
print

def	isNodeReadOnly( node ):
    for n in elements(node):
        if str(n.nodeName) == "AccessMode" and getText(n) == "RO":
            return True
        elif str(n.nodeName) == "pValue":
            try:
                regNode = lookup[getText(n)]
            except:
                regNode = None
            if not regNode:
                return True
            return isNodeReadOnly( regNode )
    return False

ADGenICam_nodes = ['AcquisitionFrameRate', 'AcquisitionFrameRateEnable',
                   'TriggerSource', 'TriggerOverlap', 'TriggerSoftware',
                   'TriggerMode', 'ExposureMode', 'ExposureAuto', 'GainAuto',
                   'PixelFormat']

# for each node
for node in doneNodes:
    nodeName = str(node.getAttribute("Name"))
    if nodeName in ADGenICam_nodes:
        print >>sys.stderr, "Skipping %s" % nodeName
        continue
    ro = isNodeReadOnly( node )
    if node.nodeName in ["Integer", "IntConverter", "IntSwissKnife"]:
        print('record(%s, "$(P)$(R)%s_RBV") {' % (GCIntegerInputRecordType, records[nodeName]))
        print '  field(DTYP, "asynInt64")'
        print '  field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_I_%s")' % nodeName
        print '  field(SCAN, "I/O Intr")'
        print '  field(DISA, "0")'        
        print '  info( autosaveFields, "%s" )' % long_autosaveFields
        print '}'
        print
        if ro:
            continue        
        print('record(%s, "$(P)$(R)%s") {' % (GCIntegerOutputRecordType, records[nodeName]))
        print '  field(DTYP, "asynInt64")'
        print '  field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_I_%s")' % nodeName
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s PINI VAL" )' % long_autosaveFields
        print '}'
        print        
    elif node.nodeName in ["Boolean"]:
        print 'record(bi, "$(P)$(R)%s_RBV") {' % records[nodeName]
        print '  field(DTYP, "asynInt32")'
        print '  field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_B_%s")' % nodeName
        print '  field(SCAN, "I/O Intr")'
        print '  field(ZNAM, "No")'
        print '  field(ONAM, "Yes")'                        
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s" )' % b_autosaveFields
        print '}'
        print
        if ro:
            continue        
        print 'record(bo, "$(P)$(R)%s") {' % records[nodeName]
        print '  field(DTYP, "asynInt32")'
        print '  field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_B_%s")' % nodeName
        print '  field(ZNAM, "No")'
        print '  field(ONAM, "Yes")'                                
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s PINI VAL" )' % b_autosaveFields
        print '}'
        print           
    elif node.nodeName in ["Float", "Converter", "SwissKnife"]:
        print 'record(ai, "$(P)$(R)%s_RBV") {' % records[nodeName]
        print '  field(DTYP, "asynFloat64")'
        print '  field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_D_%s")' % nodeName
        print '  field(PREC, "3")'        
        print '  field(SCAN, "I/O Intr")'
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s" )' % a_autosaveFields
        print '}'
        print    
        if ro:
            continue    
        print 'record(ao, "$(P)$(R)%s") {' % records[nodeName]
        print '  field(DTYP, "asynFloat64")'
        print '  field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_D_%s")' % nodeName
        print '  field(PREC, "3")'
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s PINI VAL" )' % a_autosaveFields
        print '}'
        print
    elif node.nodeName in ["StringReg", "String"]:
        print 'record(stringin, "$(P)$(R)%s_RBV") {' % records[nodeName]
        print '  field(DTYP, "asynOctetRead")'
        print '  field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_S_%s")' % nodeName
        print '  field(SCAN, "I/O Intr")'
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s" )' % string_autosaveFields
        print '}'
        print
    elif node.nodeName in ["Command"]:
        print 'record(longout, "$(P)$(R)%s") {' % records[nodeName]
        print '  field(DTYP, "asynInt32")'
        print '  field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_C_%s")' % nodeName
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s" )' % long_autosaveFields
        print '}'
        print         
    elif node.nodeName in ["Enumeration"]:
        enumerations = ""
        i = 0
        defaultVal = "0"
        epicsId = ["ZR", "ON", "TW", "TH", "FR", "FV", "SX", "SV", "EI", "NI", "TE", "EL", "TV", "TT", "FT", "FF"]
        for n in elements(node):
            if str(n.nodeName) == "EnumEntry":
                if i >= len(epicsId):
                    print >> sys.stderr, "More than 16 enum entries for %s mbbi record, discarding additional options." % nodeName
                    print >> sys.stderr, "   If needed, edit the Enumeration tag for %s to select the 16 you want." % nodeName
                    break
                name = str(n.getAttribute("Name"))
                enumerations += '  field(%sST, "%s")\n' %(epicsId[i], name[:16])  #MCB 25
                value = [x for x in elements(n) if str(x.nodeName) == "Value"]
                assert value, "EnumEntry %s in node %s doesn't have a value" %(name, nodeName)                
                if i == 0:
                    defaultVal = getText(value[0])
                enumerations += '  field(%sVL, "%s")\n' %(epicsId[i], getText(value[0]))
                i += 1                
        print 'record(mbbi, "$(P)$(R)%s_RBV") {' % records[nodeName]
        print '  field(DTYP, "asynInt32")'
        print '  field(INP,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_E_%s")' % nodeName
        print enumerations,
        print '  field(SCAN, "I/O Intr")'
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s" )' % mbb_autosaveFields
        print '}'
        print
        if ro:
            continue        
        print 'record(mbbo, "$(P)$(R)%s") {' % records[nodeName]
        print '  field(DTYP, "asynInt32")'
        print '  field(OUT,  "@asyn($(PORT),$(ADDR=0),$(TIMEOUT=1))GC_E_%s")' % nodeName
        print '  field(DOL,  "%s")' % defaultVal
        print enumerations,       
        print '  field(DISA, "0")'
        print '  info( autosaveFields, "%s PINI VAL" )' % mbb_autosaveFields
        print '}'
        print          
    else:
        print >> sys.stderr, "Don't know what to do with %s (%s)" % (nodeName, node.nodeName)
    
# tidy up
db_file.close()     
sys.stdout = stdout

# Spit out a feature screen
edl_file = open(edl_more_filename, "w")
w = 300
h = 40
x = 4
y = 48
text = ""
defFontClass	= "helvetica"
defFgColorCtrl	= 25
defBgColorCtrl	= 5
defFgColorMon	= 15
defBgColorMon	= 12

def quoteString(string):
    escape_list = ["\\","{","}",'"']
    for e in escape_list:
        string = string.replace(e,"\\"+e) 
    string = string.replace("\n", "").replace(",", ";")
    return string

def make_box():
    return """# (Rectangle)
object activeRectangleClass
beginObjectProperties
major 4
minor 0
release 0
x %(x)d
y %(y)d
w %(boxw)d
h %(boxh)d
lineColor index 14
fill
fillColor index 5
endObjectProperties

""" % globals()

def make_box_label():
    return """# (Static Text)
object activeXTextClass
beginObjectProperties
major 4
minor 1
release 1
x %(x)d
y %(laby)d
w 150
h 14
font "%(defFontClass)s-medium-r-12.0"
fontAlign "center"
fgColor index 14
bgColor index 8
value {
  "  %(name)s  "
}
autoSize
border
endObjectProperties
""" % globals()

def make_description():
    return """# (Related Display)
object relatedDisplayClass
beginObjectProperties
major 4
minor 4
release 0
x %(nx)d
y %(y)d
w 16
h 20
fgColor index 14
bgColor index 3
topShadowColor index 1
botShadowColor index 11
font "%(defFontClass)s-bold-r-10.0"
xPosOffset -100
yPosOffset -148
useFocus
buttonLabel "?"
numPvs 4
numDsps 1
displayFileName {
  0 "vimbaScreens/vimbaHelp.edl"
}
setPosition {
  0 "button"
}
symbols {
  0 "desc0=%(desc0)s,desc1=%(desc1)s,desc2=%(desc2)s,desc3=%(desc3)s,desc4=%(desc4)s,desc5=%(desc5)s"
}
endObjectProperties

""" % globals()

def make_label():
    return """
# (Static Text)
object activeXTextClass
beginObjectProperties
major 4
minor 1
release 1
x %(nx)d
y %(y)d
w %(label_w)d
h 20
font "%(defFontClass)s-bold-r-10.0"
fgColor index 14
bgColor index 3
useDisplayBg
value {
  "%(nodeName)s"
}
endObjectProperties

""" % globals()             

def make_ro():
    return """# (Text Update)
object TextupdateClass
beginObjectProperties
major 10
minor 0
release 0
x %(nx)d
y %(y)d
w 124
h 20
controlPv "$(P)$(R)%(recordName)s_RBV"
fgColor index %(defFgColorMon)d
fgAlarm
bgColor index %(defBgColorMon)d
fill
font "%(defFontClass)s-bold-r-12.0"
fontAlign "center"
endObjectProperties

""" % globals()         

def make_demand():
    return """# (Text Control)
object activeXTextDspClass
beginObjectProperties
major 4
minor 7
release 0
x %(nx)d
y %(y)d
w 60
h 20
controlPv "$(P)$(R)%(recordName)s"
font "%(defFontClass)s-bold-r-12.0"
fgColor index %(defFgColorCtrl)d
bgColor index %(defBgColorCtrl)d
editable
motifWidget
limitsFromDb
nullColor index 40
smartRefresh
changeValOnLoseFocus
autoSelect
newPos
objType "controls"
endObjectProperties

""" % globals()

def make_rbv():
    return """# (Textupdate)
object TextupdateClass
beginObjectProperties
major 10
minor 0
release 0
x %(nx)d
y %(y)d
w 60
h 20
controlPv "$(P)$(R)%(recordName)s_RBV"
fgColor index %(defFgColorMon)d
fgAlarm
bgColor index %(defBgColorMon)d
fill
font "%(defFontClass)s-bold-r-12.0"
fontAlign "center"
endObjectProperties

""" % globals() 

def make_menu():
    return """# (Menu Button)
object activeMenuButtonClass
beginObjectProperties
major 4
minor 0
release 0
x %(nx)d
y %(y)d
w 124
h 20
fgColor index %(defFgColorCtrl)d
bgColor index %(defBgColorCtrl)d
inconsistentColor index 40
topShadowColor index 1
botShadowColor index 11
controlPv "$(P)$(R)%(recordName)s"
indicatorPv "$(P)$(R)%(recordName)s_RBV"
font "%(defFontClass)s-bold-r-12.0"
endObjectProperties

""" % globals()

def make_cmd():
    return """# (Message Button)
object activeMessageButtonClass
beginObjectProperties
major 4
minor 0
release 0
x %(nx)d
y %(y)d
w 124
h 20
fgColor index %(defFgColorCtrl)d
onColor index 3
offColor index 3
topShadowColor index 1
botShadowColor index 11
controlPv "$(P)$(R)%(recordName)s.PROC"
pressValue "1"
onLabel "%(nodeName)s"
offLabel "%(nodeName)s"
3d
font "%(defFontClass)s-bold-r-12.0"
endObjectProperties

""" % globals()

label_w = 132
# Write each section
for name, nodes in structure:
    # write box
    boxh = len(nodes) * 24 + 8
    boxw = label_w + 156
    if (boxh + y > 940):
        y = 44
        w += boxw + 8
        x += boxw + 8
    laby = y - 8      
    text += make_box()
    y += 8
    h = max(y, h)    
    for node in nodes:
        nodeName = str(node.getAttribute("Name"))
        if nodeName in ADGenICam_nodes:
            print >>sys.stderr, "Skipping %s" % nodeName
            continue
        recordName = records[nodeName]
        ro = isNodeReadOnly( node )
        desc = ""
        for n in elements(node):
            if str(n.nodeName) in ["ToolTip", "Description"]:
                desc = getText(n)
        descs = ["%s: "% nodeName, "", "", "", "", ""]
        i = 0
        for word in desc.split():
            if len(descs[i]) + len(word) > 80:
                i += 1
                if i >= len(descs):
                    break
            descs[i] += word + " "
        for i in range(6):
            if descs[i]:
                globals()["desc%d" % i] = quoteString(descs[i])
            else:
                globals()["desc%d" % i] = "''"
        nx = x + 4
        text += make_description()   
        nx += 20
        text += make_label()
        nx += label_w + 4            
        if node.nodeName in ["StringReg", "String"] or ro:
            text += make_ro()
        elif node.nodeName in ["Integer", "Float", "Converter", "IntConverter", "IntSwissKnife", "SwissKnife"]:  
            text += make_demand()
            nx += 68 
            text += make_rbv() 
        elif node.nodeName in ["Enumeration", "Boolean"]:
            text += make_menu()
        elif node.nodeName in ["Command"]:
            text += make_cmd()
        else:
            print "Don't know what to do with %s (%s)" % (nodeName, node.nodeName)
        y += 24
    y += 16
    h = max(y, h)

    # Put the label on the box last so it's on top
    text += make_box_label()
    # End of write box
# End of Write each section

# tidy up
w += 4
exitX = w - 100
exitY = h - min(28, h - y)
h = exitY + 28

# Write edl file header
edl_file.write("""4 0 1
beginScreenProperties
major 4
minor 0
release 1
x 50
y 50
w %(w)d
h %(h)d
font "%(defFontClass)s-bold-r-12.0"
ctlFont "%(defFontClass)s-bold-r-12.0"
btnFont "%(defFontClass)s-bold-r-12.0"
fgColor index 14
bgColor index 3
textColor index 14
ctlFgColor1 index %(defFgColorMon)d
ctlFgColor2 index %(defFgColorCtrl)d
ctlBgColor1 index %(defBgColorMon)d
ctlBgColor2 index %(defBgColorCtrl)d
topShadowColor index 1
botShadowColor index 11
title "%(camera_name)s features - $(P)$(R)"
showGrid
snapToGrid
gridSize 4
endScreenProperties

# (Group)
object activeGroupClass
beginObjectProperties
major 4
minor 0
release 0
x 0
y 0
w %(w)d
h 30

beginGroup

# (Rectangle)
object activeRectangleClass
beginObjectProperties
major 4
minor 0
release 0
x 0
y 0
w %(w)d
h 30
lineColor index 3
fill
fillColor index 3
endObjectProperties

# (Lines)
object activeLineClass
beginObjectProperties
major 4
minor 0
release 1
x 0
y 2
w %(w)d
h 24
lineColor index 11
fillColor index 0
numPoints 3
xPoints {
  0 0
  1 %(w)d
  2 %(w)d
}
yPoints {
  0 26
  1 26
  2 2
}
endObjectProperties

# (Static Text)
object activeXTextClass
beginObjectProperties
major 4
minor 1
release 1
x 0
y 2
w %(w)d
h 24
font "%(defFontClass)s-bold-r-18.0"
fontAlign "center"
fgColor index 14
bgColor index 48
value {
  "%(camera_name)s features - $(P)$(R)"
}
endObjectProperties

# (Lines)
object activeLineClass
beginObjectProperties
major 4
minor 0
release 1
x 0
y 2
w %(w)d
h 24
lineColor index 1
fillColor index 0
numPoints 3
xPoints {
  0 0
  1 0
  2 %(w)d
}
yPoints {
  0 26
  1 2
  2 2
}
endObjectProperties

endGroup

endObjectProperties

""" %globals())

# Write edl file widgets
edl_file.write(text.encode('ascii', 'replace'))

# Write edl file exit button
edl_file.write("""# (Exit Button)
object activeExitButtonClass
beginObjectProperties
major 4
minor 1
release 0
x %(exitX)d
y %(exitY)d
w 95
h 25
fgColor index 46
bgColor index 3
topShadowColor index 1
botShadowColor index 11
label "EXIT"
font "%(defFontClass)s-bold-r-14.0"
3d
endObjectProperties
""" % globals())
edl_file.close()
    
# write the summary screen
if not os.path.exists(edl_filename):
    open(edl_filename, "w").write("""4 0 1
beginScreenProperties
major 4
minor 0
release 1
x 713
y 157
w 420
h 820
font "%(defFontClass)s-bold-r-12.0"
ctlFont "%(defFontClass)s-bold-r-12.0"
btnFont "%(defFontClass)s-bold-r-12.0"
fgColor index 14
bgColor index 3
textColor index 14
ctlFgColor1 index %(defFgColorMon)d
ctlFgColor2 index %(defFgColorCtrl)d
ctlBgColor1 index %(defBgColorMon)d
ctlBgColor2 index %(defBgColorCtrl)d
topShadowColor index 1
botShadowColor index 11
showGrid
snapToGrid
gridSize 4
endScreenProperties

# (Embedded Window)
object activePipClass
beginObjectProperties
major 4
minor 1
release 0
x 4
y 4
w 408
h 476
fgColor index 14
bgColor index 3
topShadowColor index 1
botShadowColor index 11
displaySource "file"
file "areaDetectorScreens/ADBase.edl"
sizeOfs 0
numDsps 0
noScroll
endObjectProperties

# (Embedded Window)
object activePipClass
beginObjectProperties
major 4
minor 1
release 0
x 4
y 480
w 408
h 112
fgColor index 14
bgColor index 3
topShadowColor index 1
botShadowColor index 11
displaySource "file"
file "vimbaScreens/vimbaCamera.edl"
sizeOfs 0
numDsps 0
noScroll
endObjectProperties

# (Related Display)
object relatedDisplayClass
beginObjectProperties
major 4
minor 4
release 0
x 4
y 792
w 408
h 24
fgColor index 43
bgColor index 3
topShadowColor index 1
botShadowColor index 11
font "%(defFontClass)s-bold-r-14.0"
buttonLabel "more features..."
numPvs 4
numDsps 1
displayFileName {
  0 "vimbaScreens/%(camera_name)s-features.edl"
}
setPosition {
  0 "parentWindow"
}
endObjectProperties
""" % globals() )

