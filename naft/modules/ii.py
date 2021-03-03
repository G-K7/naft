#!/usr/bin/env python3

__description__ = 'Network Appliance Forensic Toolkit - IOS Image'
__author__ = 'Didier Stevens'
__version__ = '0.0.2'
__date__ = '2013/03/24'

import hashlib
import glob
import os
import math
import pickle
import traceback
import naft.modules.uf as uf
import naft.modules.iipf as iipf
import naft.modules.impf as impf

def CiscoIOSImageFileParser(filename, options):
    global oMD5Database

    image = uf.File2Data(filename)
    if image == None:
        print('Error reading {}'.format(filename))
        return

    oIOSImage = iipf.cIOSImage(image)
    oIOSImage.Print()

    if options['md5db']:
        if options['md5db'] != None:
            oMD5Database = cMD5Database(options['md5db'])
        md5hash = hashlib.md5(image).hexdigest()
        filenameCSV, filenameDB = oMD5Database.Find(md5hash)
        if filenameCSV == None:
            print('File not found in md5 database')
        else:
            print('File found in md5 database {} {}'.format(filenameCSV, filenameDB))

    if options['verbose']:
        for oSectionHeader in oIOSImage.oELF.sections:
            print(' {:2d} {:->7s} {:d} {:d} {:08X} {:10d} {}'.format(oSectionHeader.nameIndex, \
                oSectionHeader.nameIndexString, oSectionHeader.type, oSectionHeader.flags, oSectionHeader.offset, \
                oSectionHeader.size, repr(oSectionHeader.sectionData[0:8])))

    if options['extract']:
        uf.Data2File(oIOSImage.imageUncompressed, oIOSImage.imageUncompressedName, options['extract'])

    if options['idapro']:
        uf.Data2File(oIOSImage.ImageUncompressedIDAPro(), oIOSImage.imageUncompressedName, options['idapro'])

def Entropy(data):
    result = 0.0
    size = len(data)
    if size != 0:
        bucket = [0]*256
        for char in data:
            bucket[ord(char)] += 1
        for count in bucket:
            if count > 0:
                percentage = float(count) / size
                result -= percentage*math.log(percentage, 2)
    return result

def GlobRecurse(filewildcard):
    filenames = []
    directory = os.path.dirname(filewildcard)
    if directory == '':
        directory = '.'
    for entry in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, entry)):
            filenames.extend(GlobRecurse(os.path.join(directory, entry, os.path.basename(filewildcard))))
    filenames.extend(glob.glob(filewildcard))
    return filenames

def GlobFilelist(filewildcard, options):
    if options['recurse']:
        return GlobRecurse(filewildcard)
    else:
        return glob.glob(filewildcard)

def vn(dictionary, key):
    if key in dictionary:
        return dictionary[key]
    else:
        return None

def PickleData(data):
    fPickle = open('resume.pkl', 'wb')
    pickle.dump(data, fPickle)
    fPickle.close()
    print('Pickle file saved')

def CiscoIOSImageFileScanner(filewildcard, options):
    if options['resume'] == None:
        filenames = GlobFilelist(filewildcard, options)
        countFilenames = len(filenames)
        counter = 1
        if options['log'] != None:
            f = open(options['log'], 'w')
            f.close()
    else:
        fPickle = open(options['resume'], 'rb')
        filenames, countFilenames, counter = pickle.load(fPickle)
        fPickle.close()
        print('Pickle file loaded')

    while len(filenames) > 0:
        filename = filenames[0]
        try:
            line = [str(counter), str(countFilenames), filename]
            image = uf.File2Data(filename)
            if image == None:
                line.extend(['Error reading'])
            else:
                oIOSImage = iipf.cIOSImage(image)
                if oIOSImage.oCWStrings != None and oIOSImage.oCWStrings.error == '':
                    line.extend([uf.cn(vn(oIOSImage.oCWStrings.dCWStrings, 'CW_VERSION')), uf.cn(vn(oIOSImage.oCWStrings.dCWStrings, 'CW_FAMILY'))])
                else:
                    line.extend([uf.cn(None), uf.cn(None)])
                line.extend([str(len(image)), '{:.2f}'.format(Entropy(image)), str(oIOSImage.error), \
                    str(oIOSImage.oELF.error), str(oIOSImage.oELF.countSections), str(uf.cn(oIOSImage.oELF.stringTableIndex)), \
                    uf.cn(oIOSImage.checksumCompressed, '0x%08X'), str(oIOSImage.checksumCompressed != None and \
                    oIOSImage.checksumCompressed == oIOSImage.calculatedChecksumCompressed), \
                    uf.cn(oIOSImage.checksumUncompressed, '0x%08X'), str(oIOSImage.checksumUncompressed != None and \
                    oIOSImage.checksumUncompressed == oIOSImage.calculatedChecksumUncompressed), \
                    uf.cn(oIOSImage.imageUncompressedName), uf.cn(oIOSImage.embeddedMD5)])
                if options['md5db']:
                    md5hash = hashlib.md5(image).hexdigest()
                    filenameCSV, filenameDB = oMD5Database.Find(md5hash)
                    line.extend([md5hash, uf.cn(filenameCSV), uf.cn(filenameDB)])
            strLine = ';'.join(line)
            print(strLine)
            if options['log'] != None:
                f = open(options['log'], 'a')
                f.write(strLine + '\n')
                f.close()
            counter += 1
            filenames = filenames[1:]
        except KeyboardInterrupt:
            print('KeyboardInterrupt')
            PickleData([filenames, countFilenames, counter])
            return
        except:
            traceback.print_exc()
            PickleData([filenames, countFilenames, counter])
            return

#def Main():
#    global oMD5Database
#
#    oParser = optparse.OptionParser(usage='usage: %prog [options] image\n' + __description__, version='%prog ' + __version__)
#    oParser.add_option('-v', '--verbose', action='store_true', default=False, help='verbose output')
#    oParser.add_option('-x', '--extract', action='store_true', default=False, help='extract the compressed image')
#    oParser.add_option('-i', '--idapro', action='store_true', default=False, help='extract the compressed image and patch it for IDA Pro')
#    oParser.add_option('-s', '--scan', action='store_true', default=False, help='scan a set of images')
#    oParser.add_option('-r', '--recurse', action='store_true', default=False, help='recursive scan')
#    oParser.add_option('-e', '--resume', help='resume an interrupted scan')
#    oParser.add_option('-m', '--md5db', help='compare md5 hash with provided CSV db')
#    oParser.add_option('-l', '--log', help='write scan result to log file')
#    (options, args) = oParser.parse_args()

#    if options['md5db'] != None:
#        oMD5Database = cMD5Database(options['md5db'])
#    if len(args) != 1:
#        oParser.print_help()
#        print('')
#        print('  Source code put in the public domain by Didier Stevens, no Copyright')
#        print('  Use at your own risk')
#        print('  https://DidierStevens.com')
#        return
#    elif options['scan'] :
#        CiscoIOSImageFileScanner(args[0], options)
#    elif len(args) == 1:
#        CiscoIOSImageFileParser(args[0], options)

#if __name__ == '__main__':
#    Main()
