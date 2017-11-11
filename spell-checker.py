import re
from collections import Counter
from nltk.tokenize import sent_tokenize, word_tokenize
import itertools
import sys
import time
import numpy as np
import random

reload(sys)
sys.setdefaultencoding('utf8')


def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print '%s function took %0.1f ms' % (f.func_name, (time2 - time1) * 1000.0)
        return ret

    return wrap


def learn_language_model(files, n=3, lm=None):
    """ Returns a nested dictionary of the language model based on the
    specified files. For Text Normalization i used first, lower the capital letters.
    second, i removed all the non-letter characters. i choose to do these normalizations to reduce the size of
    the vocabulary as much as possible. it will still be a valid language model that will catch most of the
    non-word and real-word. i am also processing the text data as sentences using NLTK sent_tokenizer

    Example of the returned dictionary for the text 'w1 w2 w3 w1 w4' with a
    tri-gram model:
    tri-grams:
    <> <> w1
    <> w1 w2
    w1 w2 w3
    w2 w3 w1
    w3 w1 w4
    w1 w4 <>
    w4 <> <>
    and returned language model is:
    {
    w1: {'':1, 'w2 w3':1},
    w2: {w1:1},
    w3: {'w1 w2':1},
    w4:{'w3 w1':1},
    '': {'w1 w4':1, 'w4':1}
    }

    Args:
          files (list): a list of files (full path) to process.
          n (int): length of ngram, default 3.
          lm (dict): update and return this dictionary if not None.
                     (default None).

    Returns:
        dict: a nested dict {str:{str:int}} of ngrams and their counts.
    """

    if lm is not None:
        ngrams = lm
    else:
        ngrams = {}

    for file in files:
        with open(file, "r") as f:
            for line in sent_tokenize(f.read()):
                prev_words = []
                if line == "":
                    continue
                cleaned_line = _normalize_text(line)
                words = [x for x in cleaned_line.split(" ") if x != ""]
                words = words + [""] * (n - 1)
                for word in words:
                    if word not in ngrams:
                        ngrams[word] = {}
                    if " ".join(prev_words) not in ngrams[word]:
                        ngrams[word][" ".join(prev_words)] = 0
                    ngrams[word][" ".join(prev_words)] = ngrams[word][" ".join(prev_words)] + 1
                    prev_words.append(word)
                    if len(prev_words) == n:
                        prev_words.pop(0)
    return ngrams


def _normalize_text(str):
    """
    clean the string without capital letters from any non letter or white space characters
    :param str: any string
    :return: a string with only letters and white spaces
    """
    return re.sub(r"[^a-z ]+", '', str.lower())


def create_error_distribution(errors_file):
    """ Returns a dictionary {str:dict} where str is in:
    <'deletion', 'insertion', 'transposition', 'substitution'> and the inner dict {tupple: float} represents the confution matrix of the specific errors
    where tupple is (err, corr) and the float is the probability of such an error. Examples of such tupples are ('t', 's'), ('-', 't') and ('ac','ca').
    Notes:
        1. The error distributions could be represented in more efficient ways.
           We ask you to keep it simpel and straight forward for clarity.
        2. Ultimately, one can use only 'deletion' and 'insertion' and have
            'sunstiturion' and 'transposition' derived. Again,  we use all
            four explicitly in order to keep things simple.
    Args:
        errors_file (str): full path to the errors file. File format mathces
                            Wikipedia errors list.

    Returns:
        A dictionary of error distributions by error type (dict).

    """

    error_dist = {"deletion": {}, "insertion": {}, "transposition": {}, "substitution": {}}
    with open(errors_file, "r") as f:
        text = f.read()
        char_counter = Counter(list(_normalize_text(text).lower()))
        chars_list = []
        for line in text.split("\n"):
            line = line.lower()
            if line == "":
                continue
            error_word, correct_words = line.split("->")
            error_word = _normalize_text(error_word).strip()
            correct_words = correct_words.split(", ")
            for correct_word in correct_words:
                correct_word = _normalize_text(correct_word).strip()
                chars_list += [correct_word[i:i + 2] for i in range(len(correct_word) - 1)]
                if len(correct_word) > len(error_word):
                    # deletion
                    for i in range(len(correct_word) - 1):
                        if error_word[i:i + 2] != correct_word[i:i + 2]:
                            tpl = (error_word[i:i + 1], correct_word[i:i + 2])
                            if tpl not in error_dist["deletion"]:
                                error_dist["deletion"][tpl] = 0
                            error_dist["deletion"][tpl] = error_dist["deletion"][tpl] + 1
                            break
                if len(correct_word) < len(error_word):
                    # insertion
                    for i in range(len(error_word) - 1):
                        if error_word[i:i + 2] != correct_word[i:i + 2]:
                            tpl = (error_word[i:i + 2], correct_word[i:i + 1])
                            if tpl not in error_dist["insertion"]:
                                error_dist["insertion"][tpl] = 0
                            error_dist["insertion"][tpl] = error_dist["insertion"][tpl] + 1
                            break
                if len(correct_word) == len(error_word):
                    # transposition and substitution
                    for i in range(len(correct_word) - 1):
                        if error_word[i] == correct_word[i + 1] and error_word[i + 1] == correct_word[i]:
                            # transposition
                            tpl = (error_word[i:i + 2], correct_word[i:i + 2])
                            if tpl not in error_dist["transposition"]:
                                error_dist["transposition"][tpl] = 0
                            error_dist["transposition"][tpl] = error_dist["transposition"][tpl] + 1
                            break
                        elif error_word[i] != correct_word[i]:
                            # substitution
                            tpl = (error_word[i], correct_word[i])
                            if tpl not in error_dist["substitution"]:
                                error_dist["substitution"][tpl] = 0
                            error_dist["substitution"][tpl] = error_dist["substitution"][tpl] + 1
                            break
        chars_counter = Counter(chars_list)
    for (err, corr), value in error_dist["deletion"].items():
        error_dist["deletion"][(err, corr)] = float(value) / chars_counter.get(corr)
    for (err, corr), value in error_dist["insertion"].items():
        error_dist["insertion"][(err, corr)] = float(value) / char_counter.get(corr)
    for (err, corr), value in error_dist["transposition"].items():
        error_dist["transposition"][(err, corr)] = float(value) / chars_counter.get(corr)
    for (err, corr), value in error_dist["substitution"].items():
        error_dist["substitution"][(err, corr)] = float(value) / char_counter.get(corr)
    return error_dist


def generate_text(lm, m=15, w=None):
    """ Returns a text of the specified length, generated according to the
     specified language model using the specified word (if given) as an anchor.

     Args:
        lm (dict): language model used to generate the text.
        m (int): length (num of words) of the text to generate (default 15).
        w (str): a word to start the text with (default None)

    Returns:
        A sequrnce of generated tokens, separated by white spaces (str)
    """

    n = len(lm[lm.keys()[0]].keys()[0].split(" "))

    def choose_given_context(context):
        """
        try to choose a word from the lm given a context, get all the words that has the given context and the number
        instances of that context for the word. choose by the probability compared to other words
        :param context: context for the choosing
        :return: word from the lm that has this context or empty string if there's none
        """
        # TODO stringdoc
        lst = [(key, d.get(context)) for key, d in lm.items() if context in d]
        total = sum([x[1] for x in lst])
        probas = [float(x[1]) / total for x in lst]
        try:
            return np.random.choice([x[0] for x in lst], 1, probas)[0]
        except:
            return ""

    if w is None:
        w = choose_given_context("")

    sentence = [w]

    for i in range(1, m):
        context = " ".join(sentence[max(0, i - 2):i])
        chosen_word = choose_given_context(context)
        while chosen_word == "":  # if do not know how to continue the sentence, start a new one
            chosen_word = choose_given_context("")
        sentence.append(chosen_word)
    return " ".join(sentence)


def _generate_candidates_with_proba(w, errors_dist):
    """
    create a dictionary of all the candidates and the channel probability for that candidate
    :param w: a word we want to correct
    :param errors_dist: a dictionary of {str:dict} representing the error
                            distribution of each error type (as returned by
                            create_error_distribution()
    :return: dictionary {str:prob} of all the candidates and their probabilities
    """
    correction_proba = {}
    for (err, corr), value in errors_dist["deletion"].items():
        for i in range(len(w)):
            if w[i:i + 1] == err:
                candidate = w[:i] + corr + w[i + 1:]
                correction_proba[candidate] = value
    for (err, corr), value in errors_dist["insertion"].items():
        for i in range(len(w) - 1):
            if w[i:i + 2] == err:
                candidate = w[:i] + corr + w[i + 2:]
                correction_proba[candidate] = value
    for (err, corr), value in errors_dist["substitution"].items():
        for i in range(len(w)):
            if w[i:i + 1] == err:
                candidate = w[:i] + corr + w[i + 1:]
                correction_proba[candidate] = value
    for (err, corr), value in errors_dist["transposition"].items():
        for i in range(len(w) - 1):
            if w[i:i + 2] == err:
                candidate = w[:i] + corr + w[i + 2:]
                correction_proba[candidate] = value
    return correction_proba


def correct_word(w, word_counts, errors_dist):
    """ Returns the most probable correction for the specified word, given the specified prior error distribution.

    Args:
        w (str): a word to correct
        word_counts (dict): a dictionary of {str:count} containing the
                            counts  of uniqie words (from previously loaded
                             corpora).
        errors_dist (dict): a dictionary of {str:dict} representing the error
                            distribution of each error type (as returned by
                            create_error_distribution() ).

    Returns:
        The most probable correction (str).
    """
    correction_proba = _generate_candidates_with_proba(w, errors_dist)

    best_correction = None
    best_correction_score = 0
    for word, proba in correction_proba.items():
        word_proba = float(word_counts[word] + 1) / (sum(word_counts.values()) + len(word_counts))
        score = word_proba * proba
        if score > best_correction_score:
            best_correction_score = score
            best_correction = word
    return best_correction


@timing
def correct_sentence(s, lm, err_dist, c=2, alpha=0.95):
    """ Returns the most probable sentence given the specified sentence, language
    model, error distributions, maximal number of suumed erroneous tokens and likelihood for non-error.

    Args:
        s (str): the sentence to correct.
        lm (dict): the language model to correct the sentence accordingly.
        err_dist (dict): error distributions according to error types
                        (as returned by create_error_distribution() ).
        c (int): the maximal number of tokens to change in the specified sentence.
                 (default: 2)
        alpha (float): the likelihood of a lexical entry to be the a correct word.
                        (default: 0.95)

    Returns:
        The most probable sentence (str)

    """
    sentence_words = [x for x in _normalize_text(s).split(" ") if x != ""]
    sentence_word_candidates = [_generate_candidates_with_proba(w, err_dist).keys() for w in sentence_words]
    for i in range(len(sentence_words)):
        sentence_word_candidates[i].append(sentence_words[i])

    cands_cache = {}

    def p(x, w):
        """
        calculate the probability of a given word w is actually supposed to be x
        :param x: the word from a candidate
        :param w: the matching word from the given sentence
        :return: the probability of that w supposed to be x
        """
        if x == w:
            return alpha
        if w not in cands_cache:
            cands_cache[w] = _generate_candidates_with_proba(w, err_dist)
        all_cands_for_w = cands_cache[w]
        if x in all_cands_for_w.keys():
            return all_cands_for_w[x]
        return 0.0

    def generate_sentence_candicate(n):
        """
        generate candidate with up to n errors in the sentence
        :param n: number of maximum errors in a sentence
        :return: list of candidates as array of words
        """
        if n == 0:
            return sentence_words
        indexes_to_check = itertools.combinations(range(len(sentence_words)), n)
        candidates = []
        for indexes in indexes_to_check:
            candidate_words = []
            for i, word in enumerate(sentence_words):
                if i in indexes:
                    candidate_words.append(sentence_word_candidates[i])
                else:
                    candidate_words.append([word])
            candidates += itertools.product(*candidate_words)
        return candidates

    sentence_candidates = generate_sentence_candicate(c)

    best_candidate = []
    best_candidate_proba = 0

    for j, candidate in enumerate(sentence_candidates):
        candidate_proba = 1
        for i, word in enumerate(candidate):
            word_in_org_sentence = sentence_words[i]
            candidate_proba *= p(word, word_in_org_sentence)
        if candidate_proba != 0:
            candidate_proba *= evaluate_text(" ".join(candidate), lm)
        if best_candidate_proba < candidate_proba:
            best_candidate_proba = candidate_proba
            best_candidate = " ".join(candidate)
    return best_candidate


lm_cache = {}
context_cache = {}


# @timing
def evaluate_text(s, lm):
    """ Returns the likelihood of the specified sentence to be generated by the
    the specified language model.

    Args:
        s (str): the sentence to evaluate.
        lm (dict): the language model to evaluate the sentence by.

    Returns:
        The likelihood of the sentence according to the language model (float).
    """

    hashkey = hash(frozenset(lm.get("").keys()))
    if hashkey not in lm_cache:
        lm_cache[hashkey] = sum([sum(v.values()) for v in lm.values()]), max(
            [len(x.split(" ")) for x in lm[lm.keys()[0]].keys()])
    V, n = lm_cache[hashkey]

    s = _normalize_text(s)
    # n = max([len(x.split(" ")) for x in lm[lm.keys()[0]].keys()])
    s_words = [x for x in s.split(" ") if x != ""]

    def context_freq(context):
        if context not in context_cache:
            context_cache[context] = sum([lm.get(word).get(context, 0) for word in lm.keys()])
        return context_cache[context]

    sentence_proba = 1
    for i, word in enumerate(s_words):
        context = " ".join(s_words[max(0, i - n):i])
        seq_preq = lm.get(word, {"": 0}).get(context, 0)
        context_total_freq = context_freq(context)
        if context_total_freq == 0:
            return 0
        sentence_proba *= float(seq_preq) / (context_total_freq)  # TODO think about adding smoothing
    return sentence_proba

    # def get_N_V():
    #     def get_lm_key():
    #         return hash(frozenset(lm.keys()))
    #
    #     lm_key = get_lm_key()
    #     if lm_key not in lm_cache:
    #         V = len(lm.keys())
    #         N = sum([sum(lm[word].values()) for word in lm.keys()])
    #         lm_cache[lm_key] = N, V
    #     return lm_cache[lm_key]
    #
    # s = _normalize_text(s)
    # n = len(lm[lm.keys()[0]].keys()[0].split(" "))
    # s_words = [x for x in s.split(" ") if x != ""]
    # N, V = get_N_V()
    # sentence_proba = 1
    # freq = sum(lm.get(s_words[0], {"": 0}).values())
    # first_word_proba = float(freq + 1) / (N + V)
    # sentence_proba *= first_word_proba
    # for i, word in enumerate(s_words):
    #     if i == 0:
    #         continue
    #     context = " ".join(s_words[max(0, i - n):i])
    #     if context not in context_cache:
    #         context_freq = lm.get(word, {"": 0}).get(context, 0)
    #         context_total_freq = sum([lm.get(word).get(context, 0) for word in lm.keys()])
    #         context_cache[context] = context_freq, context_total_freq
    #     else:
    #         context_freq, context_total_freq = context_cache[context]
    #     context_proba = float(context_freq + 1) / (context_total_freq + V)
    #     sentence_proba *= context_proba
    # return sentence_proba


if __name__ == '__main__':
    lm = learn_language_model(["data/trump_historical_tweets.txt"], 3, None)
    error_dist = create_error_distribution("data/wikipedia_common_misspellings.txt")
    words = []
    with open("data/trump_historical_tweets.txt", "r") as f:
        for line in f:
            cleaned_line = _normalize_text(line)
            words = words + [x for x in cleaned_line.split(" ") if x != ""]
    word_freq = Counter(words)
    correct_word("idae", word_freq, error_dist)
    print(evaluate_text(
        "@Janetlarose1: @realDonaldTrump @FaceTheNation @jdickerson WASHINGTON VERSUS TRUMP  &TRUMPS SUPPORTERS ... #TRUMPDOG",
        # TODO choose different sentence
        lm))
    # for _ in range(5):
    #     print(generate_text(lm))
    print(correct_sentence("how aer you", lm, error_dist))
    print(correct_sentence("how aer yuo", lm, error_dist))
    print(correct_sentence("how are you", lm, error_dist))  # TODO check why fail here
    pass
