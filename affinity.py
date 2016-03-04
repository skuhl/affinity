#!/usr/bin/env python3
import os, os.path, sys, math, glob, argparse, re, time, html, fnmatch
from concurrent import futures

# Requires Python 3.2 (Feb 2011) or higher since we rely on html.escape().


# If a directory is passed into this program instead of a file, all of
# the files with the extensions listed below will be concatenated into
# a single "file". Then, that single "file" will be compared with all
# of the other files. The program will print the directory name in its
# output.
extensions = [ "*.c", "*.C", "*.cpp", "*.CPP", "*.h", "*.H", "*.java", "*.JAVA" ]



# Patterns that end or begin with a zero aren't needed since patterns
# of all 1s will be slid across the text and can still identify
# similarities before and after the token that has changed. Similarly,
# patterns of all 1s except for one 0 are not very useful.
#
# Very short patterns can often be found between two files that aren't
# similar. For example, two English text files will often have the
# same sets of three consecutive tokens in them. Very short patterns
# aren't as effective as longer patterns at finding similarities such
# as copied and pasted sentences or sections of code. As patterns get
# longer, there will be fewer matches. If the number of matches stays
# high even as the pattern length increases, there is likely a high
# amount of similarity between the files.
patternWeights = [
    # pattern,           weight,  amplify factor
    ("11111",                  1,    1),
    ("111111111",              1,    1),
    ("111111111111",           2,   .8),
    ("11111111111111111",      2,   .7),
# These patterns allow for some changes to the text but still result
# in high scores if the two texts are from the same source.
    ("1001001",              1,   1),
    ("10101010101",          1,  .9),
    ("1001001001001",        2,  .8),
    ("101010101010101",      1,  .7) ]


# Split up patternWeights into separate lists.
patterns = []
weights = []
amplify = []
for i in patternWeights:
    patterns.append(i[0])
    weights.append(i[1])
    amplify.append(i[2])
# Normalize weights so they sum to 1:
weightsSum = sum(weights)
for i in range(len(weights)):
    weights[i] = weights[i]/float(weightsSum)


# __main__ sets up the arguments, but we need it globally accessible
args=None


# cacheHashes is used so we don't have to recompute the hashes for a
# given file and hash pattern. It is a dictionary and the key is
# "filename-pattern" (for example: "file.txt-111").
cacheHashes   = {}
cacheHashesSet= {} # same as cacheHashes, but hashes are stored in a frozenset()

parser = argparse.ArgumentParser(description='Calculate similarity of files. This program was originally designed to compare student homework submissions (text, programming, etc) to each other. The score that is printed out is a value between 0 and 100 where larger numbers mean the files are more similar. If this program printed "50.0 file1.txt file2.txt", approximately half of the content in file1.txt could be found in file2.txt. If you are looking for similar assignments, it is recommended that you look for high outliers and manually examine those files yourself for similarities.', epilog='All of the files that you ask this program to process should be small enough to fit comfortably in your computer\'s memory. This software is fairly effective at detecting similarities even when they might be disguised. For example, reordering different parts of a file or applying search/replace on some words will only slightly reduce the overall similarity score of the file. Adjusting spacing in the file will not substantially change the similarity score.')
parser.add_argument('file1', metavar="X.txt", nargs=1, help='One file for affinity to process')
parser.add_argument('file2', metavar="Y.txt", nargs='+', help='At least one more file for affinity to process.')
parser.add_argument('--debug', action="store_true", help="Display debugging information while running")
parser.add_argument('-v', '--verbose', action="store_true", help="Print scores as they are computed (and also print scores in a sorted list). Useful if you are comparing many files and want to see evidence of progress.")
parser.add_argument('-i', '--ignore', metavar="template.txt",
                            help="Ignores content in the given file for all similarity calculations. Useful if you expect all files to contain some content.")
parser.add_argument('-c', '--case-sensitive', action="store_true", help="The same word with different capitalizations are not similar. (Without this option, all files are lower-cased before similarity testing is applied.)")
parser.add_argument('-l', '--language', metavar="TYPE", help="Remove comments from the file before calculating similarities. If you don't use this option, similarity scores can be significantly impacted by the addition of long comments, modifying many comments, or inserting many short comments. If the language you are using has C-style comments, you should select language \'c\'. Allowed languages: c, python")
parser.add_argument('--no-symbol-padding', action="store_true", help="By default, 'int i=0;' will be considered to be exactly the same as 'int i = 0 ;' because spaces are automatically added before and after symbols before the file is tokenized (i.e., both examples are tokenized into ['int', 'i', '=', '0', ';']). If you want them to be considered to be different from each other (and to create tokens only based on the whitespace already in the file), use this option.")

parser.add_argument('-q', '--quiet', action="store_true", help="Print minimal information.")
parser.add_argument('--forward', action="store_true", help="Compare first file in list to all other files. Useful to determine how much content in the first file corresponds to material in the other files. (Can't be used with --backward)")
parser.add_argument('--backward', action="store_true", help="Compare first file in list to all other files. Useful to determine how much content in each of the other files correspond to material in the first file. (Can't be used with --forward).")
parser.add_argument('--shared', action="store_true", help="For each file listed, print a score that represents how much of the material is shared with at least one other file in the list. A small score indicates that the file shares very little material with any other. This runs more slowly the normal similarity test.")
parser.add_argument("--html", action="store_true", help="Write results to HTML files.")



def addSpacesAround(haystack, needle):
    """Given a haystack string, look for a needle and add spaces around it."""
    return haystack.replace(needle, " " + needle + " ")

def safeRead(filename):
    if not os.path.isfile(filename):
        print(filename + " is not a file.")
        return ""

    with open(filename) as f:
        try:
            return f.read()
        except UnicodeDecodeError:
            print(filename + " is not a text file. This program only supports UTF-8 and ASCII text files.")
            return "" # return an empty string so that program can continue as normal.

    return ""
        

def readFile(filename):
    """Returns the bytes in a file, throws an IOError exception if a problem occurs. If the file is actually a directory, concatenate some of the files that might be in the directory together."""
    if os.path.isfile(filename):
        return safeRead(filename)
    
    if os.path.isdir(filename):
        dirname = filename
        filesToExamine = []
        #Just look for files in directory
        #for e in extensions:
            # filesToExamine.extend(glob.glob(os.path.join(dirname, e)))
        # Search folder recursively for matching files.
        for root, dirnames, filenames in os.walk(dirname):
            for e in extensions: 
                for filename in fnmatch.filter(filenames, e):
                    filesToExamine.append(os.path.join(root, filename))

        if len(filesToExamine) == 0:
            print("Affinity did not find any files to examine in directory '"+dirname+"'. When given a directory, affinity is currently programmed to look for files with these extensions:")
            print(extensions)
            sys.exit(1)

        data = ""
        for f in filesToExamine:
            data = data + safeRead(f)
        return data

    if not os.path.exists(filename):
        print("File '"+filename+"' does not exist.")
        sys.exit(1)

    print(filename + " is neither a file nor a directory.")
    sys.exit(1)


# http://stackoverflow.com/questions/241327/python-snippet-to-remove-c-and-c-comments
def comment_remover_c(text):
    """Removes C, C++, Java style comments from a string."""
    def replacer(match):
        s = match.group(0)
        if s.startswith('/'):
            return " " # note: a space and not an empty string
        else:
            return s
    pattern = re.compile(
       r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE )
    return re.sub(pattern, replacer, text)

def comment_remover_python(text):
    """Removes Python (and shell script) style comments from a string."""
    return re.sub("#.*", "", text)


def tokenizeFile(filename, keepWhitespace=False, caseSensitive=False, language=None, symbolPadding=True):
    """Reads a file, optionally lowercases all characters, optionally
    inserts spaces around some characters to force tokenization of
    symbols, returns a list of tokens (i.e., strings from the
    file or directory)."""
    allBytes = readFile(filename)

    # Lowercase entire file unless user requested otherwise.
    if not caseSensitive:
        allBytes = allBytes.lower()

    # Remove comments if user requested it.
    if language:
        if language.lower() == "c":
            allBytes = comment_remover_c(allBytes)
        elif language.lower() == "python":
            allBytes = comment_remover_python(allBytes)


    if keepWhitespace:
        if not symbolPadding:
            # splits based on whitespace
            tokens = re.split('(\s+)', allBytes)
        else:
            # Splits most symbols into their own tokens
            tokens = re.split('(\s+|[^\s\w])', allBytes)
    else:
        if not symbolPadding:
            # splits based on whitespace
            tokens = re.split('\s+', allBytes)
        else:
            # Splits most symbols into their own tokens
            tokens = re.split('\s+|([^\s\w])', allBytes)
        
    # Remove None and empty strings which some of the split commands leave
    tokens = [ i for i in tokens if i != None and len(i)>0 ]
    return tokens


def shinglesForPattern(filename, pattern):
    """Returns a list of shingles for a given filename and pattern."""

    # TODO: We shouldn't read and tokenize the file repeatedly---once
    # for each pattern. We should just do it once.
    tokens = tokenizeFile(filename, keepWhitespace=False,
                          caseSensitive=args.case_sensitive,
                          language=args.language,
                          symbolPadding=not args.no_symbol_padding)

    # Get a list of indices where pattern[index]=='1'
    indices = [ i for i in range(len(pattern)) if pattern[i] == '1' ]

    # Generate the shingles for the pattern
    shingleList = []
    # For each possible shingle anywhere in the file
    for i in range(len(tokens)-len(pattern)):
        # Get the tokens where the pattern is '1'
        tokensToHash = [ tokens[i+j] for j in indices ]
        # Join those tokens together (with spaces in between) and add it to the shingleList
        shingleList.append(" ".join(tokensToHash))

    return shingleList


def hashesForPattern(filename, pattern):
    """Returns a list of hashes for a particular filename and pattern. Also returns a frozenset() of the hashes. If filename != args.ignore, any hashes that were requested to be ignored will be removed from the set (but not the list). The list is necessary so we can identify which tokens match. hashesForPattern() should be called for any ignored files before calling it for files that we are actually comparing."""

    shingles = shinglesForPattern(filename, pattern)

    # NOTE: We could potentially filter some hashes here so that we
    # end up with something more like a "fingerprint" for the document
    # instead a big set of hashes. For now, we hash() every shingle
    # and get an iterator.
    #
    # If we don't convert the map() into a list(), this program may
    #  run a bit faster faster but the --html option properly
    #  highlight output anymore.
    hashes = list(map(hash, shingles))

    # Add hashes and shingles to caches. We really only need the
    # shingles returned by this method if HTML output was requested.
    filepattern = filename + "-" + pattern
    cacheHashes[filepattern] = hashes

    if filename == args.ignore or args.ignore == None:
        # If this file is the ignored/template file. OR if there is nothing to ignore.
        cacheHashesSet[filepattern] = frozenset(hashes)
    else:
        # If this file is NOT the ignored/template file, we will
        # remove any hashes from the set that are supposed to be
        # ignored. This requires that the ignored files have already
        # been read in.
        ignoredHashes = cacheHashesSet[args.ignore+"-"+pattern]
        fileHashes = set(hashes)
        fileHashes.difference_update(ignoredHashes)
        cacheHashesSet[filepattern] = frozenset(fileHashes)

    return (cacheHashes[filepattern], cacheHashesSet[filepattern])

def calculateScore(filename, sharedsetLen, hashessetLen, pattern, amp, weight):
    # Calculate score for this pattern
    rawScore = 0
    if hashessetLen > 0:
        rawScore = sharedsetLen/hashessetLen
    thisScorePreAmp = 100 * rawScore
    thisScore       = 100 * (rawScore**amp)

    if args.debug:
        print("DEBUG: %s: Pattern %18s has score %0.3f (weight=%0.3f, amp=%0.3f, preampval=%0.3f, hashCount=%d)" % (filename, pattern, thisScore, weight, amp, thisScorePreAmp, hashessetLen))

    return thisScore * weight




def compareFiles(file1, file2, mode=0):
    """Returns tuple of scores. If mode==2, this function returns two scores: The first value approximates how much material from file1 is found in file2. The second value approximates how much material from file2 is found in file1. If mode > 0, only calculate how much material from file1 is found in file2."""

    if args.debug:
        print("DEBUG: Comparing %s %s" % (file1, file2))
    if file1 == file2:
        print("WARNING: You asked compareFiles() to compare a file to itself: %s" % (file1))


    # We will use matchCount to keep track of how many times each
    # token has a match. This will allow us to figure out what tokens
    # we need to highlight because there is a match.
    if args.html:
        matchCount1 = [0]*len(tokenizeFile(file1, keepWhitespace=False))
        matchCount2 = [0]*len(tokenizeFile(file2, keepWhitespace=False))

    score1 = 0.0
    score2 = 0.0
    for i in range(len(patterns)):
        pattern = patterns[i]
        weight  = weights[i]
        amp     = amplify[i]

        file1pattern = file1 + "-" + pattern
        file2pattern = file2 + "-" + pattern

        hashes1 = cacheHashes[file1pattern]
        hashes2 = cacheHashes[file2pattern]
        hashes1set = cacheHashesSet[file1pattern]
        hashes2set = cacheHashesSet[file2pattern]

        # Find the hashes in both sets, store in new set.
        sharedset = hashes1set.intersection(hashes2set)

        # Calculate the scores for this pattern and add it into our
        # cumulative scores for each file. The size of the hash1set
        # and hash2set are reduced because any item we ignored in the
        # sharedset should have also been ignored in both hashes1set
        # and hashes2set (but we don't remove hashes from those sets
        # as an optimization)
        score1 += calculateScore(file1, len(sharedset), len(hashes1set),
                                 pattern, amp, weight)
        if mode == 0:
            score2 += calculateScore(file2, len(sharedset), len(hashes2set),
                                     pattern, amp, weight)
        else:
            score2 = -1


        if args.html:

            # Get a list of indices where pattern[index]=='1'
            indices = [ i for i in range(len(pattern)) if pattern[i] == '1' ]

            # Keep track of which tokens have matches for highlighting purposes.
            if len(sharedset) > 0:
                for idx, hsh in enumerate(hashes1):
                    if hsh in sharedset:
                        for j in indices:
                            matchCount1[idx+j] += 1
                for idx, hsh in enumerate(hashes2):
                    if hsh in sharedset:
                        for j in indices:
                            matchCount2[idx+j] += 1

    # When we are done with all patterns, write HTML out with highlighted tokens
    if args.html:
        writeHTML(file1, matchCount1, score1, file2, matchCount2, score2, mode)

    if args.verbose:
        print("VERBOSE: %6.2f %-15s %-15s" % (score1, file1, file2))
        if mode==0:
            print("VERBOSE: %6.2f %-15s %-15s" % (score2, file2, file1))
    return (score1, score2)

def humanSize(num):
    """Given a number of bytes, returns a human-readable string representing the file size."""
    biggerThanBytes = False
    for x in ['bytes','KiB','MiB','GiB','TiB']:
        if num < 1024.0:
            if biggerThanBytes:
                return "%6.2f %s" % (num, x)
            else:
                return "%d %s" % (round(num), x)
        num /= 1024.0
        biggerThanBytes = True

def humanFileSize(filename, size=None):
    """Given a filename, return a human-readable string representing its size."""
    if size:
        return humanSize(size)
    else:
        if os.path.isdir(filename):
            return "dir"
        return humanSize(os.path.getsize(filename))


def mean(values):
    """Calculates the mean of a list of values."""
    if len(values) > 0:
        return sum(values)/len(values)
    return 0

def median(values):
    """Calculates the median of a sorted list of values."""
    vals = list(values)
    vals.sort()

    length = len(vals)
    if length == 0:
        return 0
    if not length % 2:
        return ( vals[length//2] + vals[length//2-1] ) / 2.0
    return vals[length//2]

def stddev(values):
    """Calculates unbiased standard deviation for a list of values."""
    meanValue = mean(values)
    n = float(len(values))
    varianceVec = map(lambda x: (x - meanValue)**2, values)
    variance = sum(varianceVec)/(n-1)
    return math.sqrt(variance)

def grubbsTest(values, alpha=0.05):
    """One-sided Grubbs test to check if maximum value is an outlier."""
    try:
        import scipy.stats
    except ImportError:
        print("Install scipy python package for outlier statistics. On Ubuntu, this package is called python3-scipy.")
        return None

    vals = list(values)
    vals.sort()

    outliers = []

    while True:
        if len(vals) < 4:
            break
        mean = sum(vals)/float(len(vals))
        s = stddev(vals)
        if s == 0:
            break
        G = (vals[-1]-mean)/s
        alpha = .05
        N = float(len(vals))
        t = scipy.stats.t.isf(alpha/N, df=N-2)
        test = (N-1)/math.sqrt(N) * math.sqrt( (t*t) / (N-2+t*t) )
        if G > test:
            outliers.append(vals[-1])
            del vals[-1]
        else:
            break

    # Sanity check:
    # Compare results to:
    # http://www.itl.nist.gov/div898/handbook/eda/section3/eda35h1.htm
    # To install outliers package in R and make sure we get the same result:
    # sudo R --vanilla
    # install.packages(c("outliers"))
    # y = c(1,2,3)
    # library(outliers)
    # grubbs.test(y,type=10)
    # Note: The test above in R will do a one-sided test and automatically try to detect which side test to apply.

    return outliers



def compareFilesPrintShared(filelist):
    """Estimate how much material in each file is from any of the other files in the list."""

    allScores = []

    print("Generating hashes from files...")
    fillCache(filelist)
    print("Comparing files...")

    # TODO: This test could be optimized!
    #  - Use multiple processes
    #  - For each file+pattern, calculate the union of all hashes once and then reuse it.

    # For each file we want to print information on
    for f in filelist:
        overallScore = 0.0;

        # For each pattern, store score + filename in a tuple
        for i in range(len(patterns)):
            pattern = patterns[i]
            weight = weights[i]
            amp = amplify[i]

            # Get a set of hashes for all of the files we are looking at
            otherHashes = set()
            for otherFile in filelist:
                if otherFile == f:
                    thisHashes = cacheHashesSet[f+"-"+pattern]
                else:
                    otherHashes = otherHashes.union(cacheHashesSet[otherFile+"-"+pattern])

            # Get hashes for this file that aren't in otherHashes. Divide
            # by how many hashes there are for this file.
            rawScore = 0;
            if len(thisHashes) > 0:
                rawScore = len(thisHashes.intersection(otherHashes))/len(thisHashes)

            thisScorePreAmp = rawScore * 100
            thisScore = rawScore**amp * 100

            if args.debug:
                print("DEBUG: Pattern %18s has score %0.3f (weight=%0.3f, amp=%0.3f, preampval=%0.3f)" % (pattern, thisScore, weight, amp, thisScorePreAmp))

            overallScore = overallScore + thisScore * weight

        # end for each pattern loop
        if args.verbose:
            print("VERBOSE: %6.2f %s" % (overallScore, f))
            
        allScores.append( (overallScore, f) )
    # end for each file for loop

    # sort data in place based on first tuple
    allScores.sort(key=lambda tup: tup[0])
    for s in allScores:
        print("%6.2f %s" % s)

    return overallScore


def compareFilesPrintResults(filelist, mode=0):
    """Compares files in the list with each other. If mode=0, compare each file with every other file (but don't compare file to itself). If mode=1, compare the first file in the list with all of the other files in the list. If mode=2, compare all of the other files in the list to the first file in the list."""

    allResults = []
    scoresOnly = []



    # Populate the hash cache
    print("Generating hashes from files...")
    fillCache(filelist)
    print("Comparing files...")


    if mode==0:
        with futures.ProcessPoolExecutor(max_workers=None) as executor:
            futureList = []
            for i in filelist:
                for j in filelist:
                    if i >= j:
                        continue
                    futureList.append( (executor.submit(compareFiles, i, j), i, j) )
            for f in futureList:
                (score1, score2) = f[0].result()
                i = f[1]
                j = f[2]
                allResults.append( (score1, i, j) )
                allResults.append( (score2, j, i) )
                scoresOnly.append(score1)
                scoresOnly.append(score2)

    # TODO: Make other modes use process pools
    if mode==1:
        for i in filelist[1:]:
            (score1, score2) = compareFiles(filelist[0],i, mode)
            allResults.append( (score1, filelist[0], i) )
            scoresOnly.append(score1)

    if mode==2:
        for i in filelist[1:]:
            (score1, score2) = compareFiles(i, filelist[0], mode)
            allResults.append( (score1, i, filelist[0]) )
            scoresOnly.append(score1)


    # sort data in place based on first tuple
    allResults.sort(key=lambda tup: tup[0])

    if args.html:
        indexhtml = open("index.html", "w")
        indexhtml.write(getHTMLheader())
        indexhtml.write("<div style='font-size: 160%; font-weight: bold; color: #34495e; margin:12px'>Affinity results</div>\n")
        indexhtml.write("<table class='summarytable'>")
        indexhtml.write("<td><b>Score</b></td><td colspan='2'><b>Filename or directory</b></td>")

    for i in allResults:
        print("%6.2f %-15s %-15s" % (i[0], i[1], i[2]))

    if args.html:
        for i in reversed(allResults):
            if i[1] > i[2]:
                thisHTMLfile = str(abs(hash(i[2] + i[1])))+".html"
            else:
                thisHTMLfile = str(abs(hash(i[1] + i[2])))+".html"
            indexhtml.write("<tr>"
                            "<td style='text-align: right'>"
                            "<a href='%s'>%0.2f</a>"
                            "</td>"
                            "<td>%s <span class='filesize'>%s</span></td>"
                            "<td>%s <span class='filesize'>%s</span></td>"
                            "</tr>" % (thisHTMLfile, i[0], 
                                       html.escape(i[1]), humanFileSize(i[1]),
                                       html.escape(i[2]), humanFileSize(i[2])))

    if args.html:
        indexhtml.write("</table>")
        indexhtml.write("</body></html>")
        indexhtml.close()

    if not args.quiet:
        print("")

        if len(filelist) > 2 and len(scoresOnly) > 0:
            scoreMean = mean(scoresOnly)
            scoreMedian = median(scoresOnly)
            scoreStd = stddev(scoresOnly)
            scoreMin = min(float(s) for s in scoresOnly)
            scoreMax = max(float(s) for s in scoresOnly)

            totalFileSize = 0
            for f in filelist:
                totalFileSize += os.path.getsize(f)
            elapsedTime = time.time()-START_TIME
            print("%15s %6d"    % ("File pairs:", len(scoresOnly)))
            print("%15s %s"    % ("Total filesize:", humanFileSize(None, size=totalFileSize)))
            print("%15s %6.2f   seconds"   % ("Elapsed time:", elapsedTime))
            print("%15s %8.4f seconds per file pair"   % ("", elapsedTime/len(scoresOnly)))
            print("%15s %8.4f seconds per kilobyte"   % ("", elapsedTime/(totalFileSize/(1024))))
            print("%15s %6.2f" % ("Average:", scoreMean))
            print("%15s %6.2f" % ("Median:", scoreMedian))
            print("%15s %6.2f -- %0.2f" % ("Range", scoreMin, scoreMax))
            print("%15s %6.2f" % ("Std dev:", scoreStd))
            outliers = grubbsTest(scoresOnly)
            if outliers != None:  # If we have scipy installed
                outliers.sort()
                if len(outliers) == 1:
                    print("%15s The highest value is an outlier." % ("Outliers:"))
                elif len(outliers) == 0:
                    print("%15s None!" % ("Outliers:"))
                else:
                    print("%15s Scores >= %.2f are outliers (there are %d of them)." % ("Outliers:", outliers[0], len(outliers)))



def getHTMLheader(title="Affinity"):
    header = "<!DOCTYPE html>\n" \
             "<html>\n" \
             "<meta charset='utf-8'>\n" \
             "<style>\n" \
             "body { font-family: Calabri, Helvetica, DejaVu Sans, Arial, sans-serif; background-color: #eee }\n" \
             "code { font-family: Consolas, Menlo, Monaco, Lucida Console, Liberation Mono, DejaVu Sans Mono, Bitstream Vera Sans Mono, Courier New, monospace, serif; }\n" \
             "code b { color: #c0392b }\n" \
             "abbr { border-bottom: 1px dotted black; }\n" \
             "a:link    { color: #2980b9; font-weight: normal }\n" \
             "a:visited { color: #3498db; font-weight: normal }\n" \
             "a:hover   { color: #9b59b6; font-weight: normal }\n" \
             ".filenametitle { font-size: 120%; font-weight: bold; }\n" \
             ".filesize  { font-size: 70%%; color: #7f8c8d }\n" \
             ".listing { border: solid 1px #7f8c8d; padding: 8px; background-color: white }\n" \
             ".space { color: #ccc; font-weight: normal }\n" \
             ".navigation  { margin-top: 15px; margin-bottom: 15px }\n" \
             ".summarytable  { border-collapse: collapse; background-color: white }\n" \
             ".summarytable td { border: 1px solid #7f8c8d; padding: .6em }\n" \
             "</style>\n" \
             "<head><title>"+title+"</title></head>\n" \
             "<body>\n"
    return header

def writeHTMLFormattedFile(htmloutputfile, filename, matchCount):
    """This writes a <code></code> block for a given file."""
    f = htmloutputfile
    output = []
    f.write("<div class='listing'><code>\n")

    tokensWS = tokenizeFile(filename, keepWhitespace=True, caseSensitive=True, language=args.language, symbolPadding=not args.no_symbol_padding)

    # Loop through the tokens (including whitespace tokens). The Nth
    # non-whitespace token should correspond to the Nth value in
    # matchCount (which indicates how many matches there are for that
    # token)
    tokensIndex = 0
    boldOn = False
    for tws in tokensWS:
        # do HTML escape on tokens
        tws = html.escape(tws, quote=False)

        if tws[0].isspace():
            # Replace newlines
            tws = tws.replace('\n', "&#9166;<br>\n")
            # Use spaces to make tab 8 spaces but still allow the browser to linebreak the space
            tws = tws.replace('\t', "&#8614;"+"&emsp;"*7)
            # Replace spaces with middle dots
            if len(tws) > 1:
                tws = tws.replace(' ', "&middot;<wbr>")

            f.write("<span class='space'>"+tws+"</span>")
        else:
            if matchCount[tokensIndex] > 0:
                # make sure bold is turned on
                if not boldOn:
                    boldOn = True
                    f.write("<b>")
            else:
                # make sure bold is turned off
                if boldOn:
                    boldOn = False
                    f.write("</b>")
            f.write(tws)
            tokensIndex = tokensIndex+1
    if boldOn:
        f.write("</b>")

    f.write("</code></div>\n")

def writeHTML(filename, matchCount1, score1, otherFile, matchCount2, score2, mode):
    """Writes an HTML file which shows the similarities between a pair of files. If mode==0, the two files are each compared to each other so each one will have a score. If mode > 0, only the left file will have a score."""

    if(filename > otherFile):
        print("The same HTML file may have been written twice: "+filename+" "+otherFile)

    htmlfile = str(abs(hash(filename + otherFile)))+".html";
    with open(htmlfile, "w") as f:
        f.write(getHTMLheader(filename + " vs " + otherFile))

        f.write("<div class='navigation'><a href='index.html' style='font-size: 120%; font-weight: bold;'>&#8672; Return to affinity summary</a></div>")
        if mode==0:
            f.write("<p><b>Note:</b> The left and right files may be swapped from what you might expect because this single page is used for two different similarity scores.")

        f.write("<table width='100%'><tr><td width='50%' style='vertical-align: top'>\n")
        f.write("<span class='filenametitle'>%s (<abbr title='This score estimates how much material in %s was found in %s'>score: %0.2f</abbr>)</span>\n" % (filename, filename, otherFile, score1))
        f.write("<span class='filesize'>"+humanFileSize(filename)+"</span>")
        writeHTMLFormattedFile(f, filename, matchCount1)
        f.write("</td><td width='50%' style='vertical-align: top'>\n")
        if mode == 0:
            f.write("<span class='filenametitle'>%s (<abbr title='This score estimates how much material in %s was found in %s'>score: %0.2f</abbr>)</span>\n" % (otherFile, otherFile, filename, score2))
        else:
            f.write("<span class='filenametitle'>%s</span>\n" % (otherFile))
        f.write("<span class='filesize'>"+humanFileSize(otherFile)+"</span><br>\n")
        writeHTMLFormattedFile(f, otherFile, matchCount2)
        f.write("</td></tr></table>\n")

        f.write("<div class='navigation'><a href='index.html' style='font-size: 120%; font-weight: bold;'>&#8672; Return to affinity summary</a></div>")

        f.write("<ul>\n")
        if args.language:
            f.write("<li><b>Comments are not shown</b> because <i>--language " + args.language + "</i> was specified. Affinity also ignored comments while calculating similarities.\n")
        else:
            f.write("<li>You can use the <i>--language</i> flag to exclude comments from the analysis.\n")
        if args.no_symbol_padding:
            f.write("<li>Affinity is treating '1+1=2' to be different from '1 + 1 = 2' because <i>--no-symbol-padding</i> was used.\n")
        else:
            f.write("<li>Affinity is treating '1+1=2' to be the same as '1 + 1 = 2'. Use <i>--no-symbol-padding</i> to change this behavior.\n")
        if args.case_sensitive:
            f.write("<li>Words with different capitalizations are treated as if they are different words because <i>--case-sensitive</i> was used.</li>\n")
        else:
            f.write("<li>The capitalization of words does not matter. Use <i>--case-sensitive</i> to change this behavior.</li>\n")
        if args.ignore:
            f.write("<li>Any material in <b>"+args.ignore+"</b> is not highlighted below because <i>--ignore</i> was used.</li>\n")
        else:
            f.write("<li>If you don't want affinity to highlight similarities for certain material, consider using <i>--ignore</i>. The ignore option is useful in situations where you have material that you expect will be in the files.</li>\n")
        f.write("</ul>\n")

        f.write("</body>")
        f.write("</html>")


def fillCache(filelist):
    """Populate the hash cache."""

    # Read ignored file first so that when we read other files, we can
    # remove the hashes that are supposed to be ignored.
    if args.ignore:
        for pattern in patterns:
            hashesForPattern(args.ignore, pattern)


    with futures.ProcessPoolExecutor(max_workers=None) as executor:
        allfilelist = list(filelist)

        futureList = []
        for filename in allfilelist:
            for pattern in patterns:
                filepattern = filename + "-" + pattern
                #(cacheHashes[filepattern], cacheHashesSet[filepattern]) = hashesForPattern(filename, pattern)
                futureList.append( (executor.submit(hashesForPattern, filename, pattern),
                                    filepattern))
        for f in futureList:
            (hashes, hashesSet) = f[0].result()
            cacheHashes[f[1]] = hashes
            cacheHashesSet[f[1]] = hashesSet


        

if __name__ == "__main__":
    START_TIME=time.time()

    args = parser.parse_args()

    files = args.file1
    files.extend(args.file2)

    if args.debug:
        args.verbose = True

    # go through the arguments that are mutually exclusive to make
    # sure that no more than one of them are used!
    mutExArgs = 0
    if args.forward:
        mutExArgs += 1
    if args.backward:
        mutExArgs += 1
    if args.shared:
        mutExArgs += 1

    if mutExArgs > 1:
        print("You can only use one of the following arguments at a time:")
        print("--forward")
        print("--backward")
        print("--shared")
        sys.exit(1)

    if args.forward:
        compareFilesPrintResults(files, mode=1)
    elif args.backward:
        compareFilesPrintResults(files, mode=2)
    elif args.shared:
        compareFilesPrintShared(files)
    else:
        compareFilesPrintResults(files)

