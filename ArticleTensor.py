import os
import nltk
import numpy as np
import tensorly as tl
from tensorly.decomposition import parafac


def get_fullpath(*path):
    """
    Returns an absolute path given a relative path
    """
    path = [os.path.curdir] + list(path)
    return os.path.abspath(os.path.join(*path))


class ArticleTensor:
    def __init__(self, path):
        """
        :param path: path to all the articles. Must contain Fake, Fake_title, Real, Real_title
        """
        self.path = path
        self.vocabulary = {}
        self.index_to_words = []
        self.words_to_index = {}
        self.articles = {
            'fake': [],
            'real': []
        }

    def get_content(self, filename):
        """
        Get the content of a given file
        :param filename: path to file to open
        """
        with open(filename, 'r', encoding="utf-8", errors='ignore') as document:
            content = document.read().replace('\n', '').replace('\r', '')
        content_words_tokenized = nltk.word_tokenize(content.lower())
        # Add words in the vocab
        for word in content_words_tokenized:
            self.vocabulary[word] = 1 if word not in self.vocabulary.keys() else self.vocabulary[word] + 1
        return content_words_tokenized

    def get_articles(self, articles_directory, number_fake, number_real):
        files_path_fake = get_fullpath(self.path, articles_directory, 'Fake')
        files_path_fake_titles = get_fullpath(self.path, articles_directory, 'Fake_titles')
        files_path_real = get_fullpath(self.path, articles_directory, 'Real')
        files_path_real_titles = get_fullpath(self.path, articles_directory, 'Real_titles')
        files_fake = np.random.choice(os.listdir(files_path_fake), number_fake)  # Get all files in the fake directory
        files_real = np.random.choice(os.listdir(files_path_real), number_real)  # Get all files in the real directory
        for file in files_fake:
            self.articles['fake'].append({
                'content': self.get_content(get_fullpath(files_path_fake, file)),
                'title': self.get_content(get_fullpath(files_path_fake_titles, file))
            })
        for file in files_real:
            self.articles['real'].append({
                'content': self.get_content(get_fullpath(files_path_real, file)),
                'title': self.get_content(get_fullpath(files_path_real_titles, file))
            })

    def build_word_to_index(self, in_freq_order=True):
        """
        Build the index_to_word and word_to_index list and dict
        :param in_freq_order: if True, list in in order of appearance frequency
        """
        # Add <unk> to vocabulary
        self.vocabulary['<unk>'] = 0
        if in_freq_order:
            vocab = sorted(list(self.vocabulary.items()), key=lambda x: x[1], reverse=True)
        else:
            vocab = list(self.vocabulary.items())
        self.index_to_words, frequencies = list(zip(*vocab))
        self.index_to_words = list(self.index_to_words)
        self.words_to_index = {word: index for index, word in enumerate(self.index_to_words)}

    def get_co_occurrence_matrix(self, article, window, use_frequency=True):
        """
        Get the co occurrence matrix of an article
        :param article:
        :param window: window to consider the words around
        :param use_frequency: if True, co occurrence matrix has the count with each other words else only a boolean
        """
        half_window = window // 2  # half to the right, half to the left
        co_occurrence_matrix = np.zeros((len(self.index_to_words), len(self.index_to_words)))
        for k, word in enumerate(article):
            neighbooring_words = (article[max(0, k - half_window): k] if k > 0 else []) + (
                article[k + 1: min(len(article), k + 1 + half_window)] if k < len(article) - 1 else [])
            word_key = self.get_word_index(word)
            for neighbooring_word in neighbooring_words:
                if use_frequency:
                    co_occurrence_matrix[word_key][self.get_word_index(neighbooring_word)] += 1
                else:
                    co_occurrence_matrix[word_key][self.get_word_index(neighbooring_word)] = 1
        return co_occurrence_matrix

    def get_tensor(self, window, num_unknown, use_frequency=True):
        articles = [article['content'] for article in self.articles['fake']] + [article['content'] for article in
                                                                                self.articles['real']]
        labels = []
        for k in range(len(articles)):
            if k < len(self.articles['fake']):
                labels.append(-1)
            else:
                labels.append(1)
        # Shuffle the labels and articles
        articles, labels = list(zip(*np.random.permutation(list(zip(articles, labels)))))
        labels = list(labels)
        labels_untouched = labels[:]
        # Add zeros randomly to some labels
        for k in range(num_unknown):
            labels[k] = 0
        articles, labels, labels_untouched = list(zip(*np.random.permutation(list(zip(articles, labels, labels_untouched)))))

        tensor = np.zeros((len(self.index_to_words), len(self.index_to_words), len(articles)))
        for k, article in enumerate(articles):
            tensor[:, :, k] = self.get_co_occurrence_matrix(article, window, use_frequency)
        return tensor, labels, labels_untouched

    def get_word_index(self, word):
        """
        Returns the index of a word if known, the one of <unk> otherwise
        """
        if word in self.index_to_words:
            return self.words_to_index[word]
        return self.words_to_index['<unk>']

    @staticmethod
    def get_parafac_decomposition(tensor, rank):
        """
        Returns
        :param tensor:
        :param rank:
        :return: 3 matrices: (vocab, rank) (vocab, rank) and (num of articles, rank)
        """
        tensor = tl.tensor(tensor)
        return parafac(tensor, rank=rank)
