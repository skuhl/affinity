% AFFINITY(1) Affinity User Manual
% Scott Kuhl
% June 3, 2014

# NAME

affinity - measure of similarity between text files

# SYNOPSIS

affinity [*options*] [*input-files*]...

# DESCRIPTION

Affinity measures the similarity between text files. It was originally designed to help course instructors look for similarities in source code that students turn in for programming assignments. However, it can provide similarity scores for any pair of text files. If no other options are provided, affinity will take the list of *input-files*, enumerate every possible pair of files, and then calculates and prints the amount of similarity of those tiles. The output is sorted by the similarity scores.

Due to the algorithm used by affinity (described in the IMPLEMENTATION section below), the scores provide a rough estimate of similarity that is not easy to concisely describe. The scores range from 0 to 100. As an example, if affinity printed "95.32 file1.txt file2.txt", it would mean that a large percentage of the material in file1.txt is similar to material somewhere in file2.txt. Affinity might also print "20.32 file2.txt file1.txt" which indicates that only a small percentage of material in file2.txt is similar to material somewhere in file1.txt. Future revisions of this software may result in different scores for the same set of files. Since the exact meaning of any particular score is not obvious, it is best to focus on the relative differences between multiple scores since high scores almost certainly mean more similarity.

In the context of detecting inappropriate collaboration between students on an assignment, it is important to note that affinity is not intended to be a substitute for manually looking at files to determine if they are similar or not. Instead, affinity aims to provide some guidance for what pairs of files might need additional scrutiny. Instructors should look for outliers in the scores instead of looking for scores above a certain threshold. If python3-scipy is installed, affinity will apply a statistical test (one-sided Grubbs' test for outliers) which can help determine if the highest score(s) might be outliers or not. Students may have a difficult time using affinity to find ways to collaborate while also avoiding detection since it is difficult to determine which scores might be outliers (since they don't have access to all of their peers' solutions).

Affinity can highlight, in general, tokens that seem to be similar between the files, when *--html* output is enabled. However, the output does not allow you to easily see where a token in one file corresponds with a token in another similar file. Software packages such as <http://meldmerge.org/> or diff can help compare files in more detail.

Affinity has not been optimized to handle large numbers of files or very large files. It may run slowly in some circumstances. For example, it might take 5 seconds on a typical computer to compare 100 submissions for a basic C programming assignment.

# OPTIONS

Pass the *--help* argument to affinity for a full description of all available options for affinity.


# FREQUENTLY ASKED QUESTIONS

**Does affinity support binary files?** No. Affinity only works on ASCII and UTF-8 text files. The algorithm relies on whitespace between words to be able to tokenize the file.

**Does affinity support text files?** Yes, affinity will support any text file---but it assumes that there are many areas of whitespace in the file so that it can be divided into tokens.

**Does it work with source code for some programming languages besides C/C++/Python?** Yes. Affinity can work with any text file. If you are concerned about students hiding similarities by modifying, inserting, or removing comments int he source code, you should make sure that the comments are removed by the *-l/--language* option. If affinity doesn't support the language that you are interested, you can write a regular expression that identifies comments in the language and modify the affinity Python script. If you add support for another language, please consider sharing your code with the affinity author so it can be included in future versions.

**I'm a computer science instructor teaching a class. What options should I use with affinity to determine if C/C++/Java programs are the same?** It is recommended that you run affinity with the *-l/--language* option appropriate for the language that you are using. If you given students "template" code that they were to base their solution off of, you should use the *-i/--ignore* option to tell affinity to ignore the content in that template file. Nonetheless, you still might want to run affinity with different options depending on what kinds of similarities you are looking for. General tips include:

* Make sure that you include any solutions that students might have copied when you are looking for similarities in student submissions. This includes the instructor's solution, submissions for a previous semester of the course, or known solutions that might be available online.
* If you want affinity to measure similarities between comments in the source code in addition to the other non-comment material in the file, do _not_ use *-l/--language*.
* If you don't want extensive revisions/additions/removals of comments in source code to be considered a difference between files, use *-l/--language*.
* By default, "int i=0" will be treated the same as "int i = 10 ;" because extra padding (or whitespace) is added around common symbols by default. If you want to disable this behavior so that extra whitespace is _not_ added around symboles, use *--no-symbol-padding*
* By default, "int count;" and "int Count;" to be treated as being the same. If you want affinity to recognize them as being different, use *-c/--case-sensitive*.
* If you want to see how much of the student submission is material corresponds to template code that you might have provided them, try using *affinity --backward template.txt file1.txt file2.txt file3.txt ...*
* If you want to see how much of the template code (that students were asked to base their solution on) is in each of the student submissions, try using *affinity --forward template.txt file1.txt file2.txt file3.txt ...*
* If affinity detects outliers, you should carefully examine the submissions. If affinity does not detect outliers, you still might want to examine some of the highest scoring file pairs. The outlier test identifies statistically significant outliers, but does not necessarily identify when there is inappropriate behavior.
* When you are manually examining a file for similarities after affinity identified it, you might want to check for similarities in whitespace since affinity makes no distinction between different types and amounts of whitespace. For example, do the files use spaces and tabs in the same way? Do both files use the whitespace in the same way even though most students might use different styles? Are there similarities in whitespace at the end of lines?


# IMPLEMENTATION

The algorithm used by affinity is straightforward and its code is reasonably easy to understand. It is a single file Python 3 script that follows the steps described below:

1. Read in the files from disk into a Python string. If the user specified a directory instead of a file, we look for files in that directory (based on the "extensions" variable at the top of the Python script), and concatenate all of files into a single string.

2. Lowercase all characters in the string. Skip this step if *-c* or *--case-sensitive* option is used.

3. Add whitespace padding around symbols such as commas, periods, etc. in the string. For example, if we don't ensure that there is always a space before a semicolons, the semicolon might be treated as being a part of whatever appears before it. Skip this step if *--no-symbol-padding* option is used.

4. Split the string into tokens based on whitespace.

5. Create hashes according to a specific pattern from the tokens. For example, assume that a file contains the tokens ['hello', 'my', 'name', 'is', 'affinity', 'and', 'i', 'detect', 'similarities']. If we apply the pattern "111" to these tokens, it would create a 3-shingling (<https://en.wikipedia.org/wiki/W-shingling>) from the tokens has the following shingles:  ['hello', 'my', 'name']  and ['my', 'name', 'is']  and ['name', 'is', 'affinity'] etc until the last shingle ['i', 'detect', 'similarities']. If the pattern includes a '0' in it, we skip a token during shingling. If we apply the pattern '101' to the same tokens, we'd generate the following shingles: ['hello', 'name'] and ['my', 'is'] and ['name', 'affinity'] etc until the last shingle ['i', 'similarities']. Skipping tokens in this fashion can help affinity detect similarities when some tokens have been renamed.

6. For each file and each pattern affinity uses (such as "111" pattern, described in the previous step), we store the set of shingles. However, instead of storing the shingles directly, we hash them. For example the shingle ['i', 'detect', 'similarities'] is converted into the string "i detect similarities" and Python's hash() function is applied to convert the string into an integer. The hashes are stored in a Python set.

7. If the *-i* or *--ignore* option specifies content that we should ignore, we generate sets of shingles for the contents of that file. We also hash those shingles and store them in a Python set. When we shingle the files in step 6, we don't store shingles that we are supposed to ignore.

8. Assume that we are working on some pattern for file1.txt and file2.txt and we have a set of shingles (or, more specifically, hashes of those shingles) for both files. We simply calculate how large the intersection of the shingle sets for file1.txt and file2.txt are. Then, we divide that size by the number of shingles for file1.txt. This tells us the percentage of shingles for file1.txt that appear in file2.txt for the given pattern that we are working on.

9. Once a percentage is calculated for each pattern that affinity is examining, we must calculate a single percentage to display to the user. We use two main ideas to calculate the final score: (1) We can apply a weighted average to make the score from some patterns have a larger affect than the score from other patterns. (2) We can "amplify" scores. For example, if even a small amount of matching (i.e., a score of 10%) is very significant for patterns that are very long, then that score can be amplified. If we use an amplification factor of "0.3" and the original score was 0.1, then we calculate the amplified score as: 0.1^0.3 = 0.5. (Note: Small amplification factors mean large amounts of amplification). This calculation keeps the final score between 0 and 1. The scores are multiplied by 100 when printed to the screen. Since the method we use to amplify and average scores is arbitrary, the final computed score is arbitrary and has no direct meaning. Therefore, a score of 50% doesn't definitively mean that 50% of the first files' material is in the second file. The current patterns, weights, and amplification factors are known to work reasonably well to detect similarities between programming assignments in computer science classes.



# SEE ALSO

There are several software packages available which perform similar analysis on files, including:

MOSS - Measure of Software Similarity <http://theory.stanford.edu/~aiken/moss/>

SIM - Software and text similarity tester <http://dickgrune.com/Programs/similarity_tester/>

Simian - Similarity analyser <http://www.harukizaemon.com/simian/>

The Sherlock Plagiarism Detector - <http://sydney.edu.au/engineering/it/~scilect/sherlock/>

simhash - <http://svcs.cs.pdx.edu/gitweb?p=simhash.git;a=summary>

# CONTRIBUTING

The source code for affinity is available at: <https://github.com/skuhl/affinity>.
