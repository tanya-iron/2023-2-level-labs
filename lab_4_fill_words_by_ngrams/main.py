"""
Lab 4.

Top-p sampling generation and filling gaps with ngrams
"""
# pylint:disable=too-few-public-methods, too-many-arguments
import json
import math
import random

from lab_3_generate_by_ngrams.main import (BeamSearchTextGenerator, GreedyTextGenerator,
                                           NGramLanguageModel, TextProcessor)


class WordProcessor(TextProcessor):
    """
    Handle text tokenization, encoding and decoding.
    """

    def _tokenize(self, text: str) -> tuple[str, ...]:  # type: ignore
        """
        Tokenize text into tokens, separating sentences with special token.

        Punctuation and digits are removed. EoW token is appended after the last word in sentence.

        Args:
            text (str): Original text

        Returns:
            tuple[str, ...]: Tokenized text

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.
        """
        if not isinstance(text, str) or not text:
            raise ValueError('Trying to tokenize empty or not string text')
        tokens = []
        bad_end_symbols = ('!', '.', '?')
        for word in text.lower().split():
            clean_word = ''.join(filter(str.isalpha, word))
            if not clean_word:
                continue
            tokens.append(clean_word)
            if word[-1] in bad_end_symbols:
                tokens.append(self._end_of_word_token)
        return tuple(tokens)

    def _put(self, element: str) -> None:
        """
        Put an element into the storage, assign a unique id to it.

        Args:
            element (str): Element to put into storage

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.
        """
        if not isinstance(element, str) or not element:
            raise ValueError('Trying to put not string or empty element')
        if element not in self._storage:
            self._storage[element] = len(self._storage)

    def _postprocess_decoded_text(self, decoded_corpus: tuple[str, ...]) -> str:  # type: ignore
        """
        Convert decoded sentence into the string sequence.

        Special symbols are replaced with spaces.
        The first word is capitalized, resulting sequence must end with a full stop.

        Args:
            decoded_corpus (tuple[str, ...]): Tuple of decoded tokens

        Returns:
            str: Resulting text

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.
        """
        if not isinstance(decoded_corpus, tuple) or not decoded_corpus:
            raise ValueError('Trying to postprocess non-tuple or empty text')
        sentences = ' '.join(decoded_corpus).split(self._end_of_word_token)
        decoded_text = '. '.join([sentence.strip().capitalize() for sentence in sentences])
        if decoded_text[-1] == ' ':
            return decoded_text[:-1]
        return f"{decoded_text}."


class TopPGenerator:
    """
    Generator with top-p sampling strategy.

    Attributes:
        _model (NGramLanguageModel): NGramLanguageModel instance to use for text generation
        _word_processor (WordProcessor): WordProcessor instance to handle text processing
        _p_value (float) : Collective probability mass threshold for generation
    """

    def __init__(
        self, language_model: NGramLanguageModel, word_processor: WordProcessor, p_value: float
    ) -> None:
        """
        Initialize an instance of TopPGenerator.

        Args:
            language_model (NGramLanguageModel):
                NGramLanguageModel instance to use for text generation
            word_processor (WordProcessor): WordProcessor instance to handle text processing
            p_value (float): Collective probability mass threshold
        """
        self._word_processor = word_processor
        self._model = language_model
        self._p_value = p_value

    def run(self, seq_len: int, prompt: str) -> str:  # type: ignore
        """
        Generate sequence with top-p sampling strategy.

        Args:
            seq_len (int): Number of tokens to generate
            prompt (str): Beginning of the sequence

        Returns:
            str: Generated sequence

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if sequence has inappropriate length,
                or if methods used return None.
        """
        if (not isinstance(seq_len, int) or not seq_len > 0
                or not isinstance(prompt, str) or not prompt):
            raise ValueError('Trying to run with bad prompt or seq_len')
        encoded = self._word_processor.encode(prompt)
        if not encoded:
            raise ValueError('Encoded returned None')
        current_len = 0
        while current_len < seq_len:
            new_tokens = self._model.generate_next_token(encoded)
            if new_tokens is None:
                raise ValueError('Next token was not generated')
            if not new_tokens:
                break
            sorted_tokens = sorted(list(new_tokens.items()),
                                   key=lambda x: (x[1], x[0]), reverse=True)
            min_tokens = []
            freq_sum = 0
            for token in sorted_tokens:
                if freq_sum < self._p_value:
                    freq_sum += token[1]
                    min_tokens.append(token[0])
            random_token = random.choice(min_tokens)
            encoded += (random_token,)
            current_len += 1
        decoded = self._word_processor.decode(encoded)
        if not decoded:
            raise ValueError('Decoded returned None')
        return decoded


class GeneratorTypes:
    """
    A class that represents types of generators.

    Attributes:
        greedy (int): Numeric type of Greedy generator
        top_p (int): Numeric type of Top-P generator
        beam_search (int): Numeric type of Beam Search generator
    """

    def __init__(self) -> None:
        """
        Initialize an instance of GeneratorTypes.
        """
        self.greedy = 0
        self.top_p = 1
        self.beam_search = 2
        self.types = {self.greedy: 'Greedy Generator',
                      self.top_p: 'Top-P Generator',
                      self.beam_search: 'Beam Search Generator'}

    def get_conversion_generator_type(self, generator_type: int) -> str:  # type: ignore
        """
        Retrieve string type of generator.

        Args:
            generator_type (int): Numeric type of the generator

        Returns:
            (str): Name of the generator.
        """
        return self.types[generator_type]


class GenerationResultDTO:
    """
    Class that represents results of QualityChecker.

    Attributes:
        __text (str): Text that used to calculate perplexity
        __perplexity (float): Calculated perplexity score
        __type (int): Numeric type of the generator
    """

    def __init__(self, text: str, perplexity: float, generation_type: int):
        """
        Initialize an instance of GenerationResultDTO.

        Args:
            text (str): The text used to calculate perplexity
            perplexity (float): Calculated perplexity score
            generation_type (int):
                Numeric type of the generator for which perplexity was calculated
        """
        self.__text = text
        self.__perplexity = perplexity
        self.__type = generation_type

    def get_perplexity(self) -> float:  # type: ignore
        """
        Retrieve a perplexity value.

        Returns:
            (float): Perplexity value
        """
        return self.__perplexity

    def get_text(self) -> str:  # type: ignore
        """
        Retrieve a text.

        Returns:
            (str): Text for which the perplexity was count
        """
        return self.__text

    def get_type(self) -> int:  # type: ignore
        """
        Retrieve a numeric type.

        Returns:
            (int): Numeric type of the generator
        """
        return self.__type

    def __str__(self) -> str:  # type: ignore
        """
        Prints report after quality check.

        Returns:
            (str): String with report
        """
        return f"Perplexity score: {self.__perplexity}\n" \
               f"{GeneratorTypes().get_conversion_generator_type(self.__type)}\n" \
               f"Text: {self.__text}\n"


class QualityChecker:
    """
    Check the quality of different ways to generate sequence.

    Attributes:
        _generators (dict): Dictionary with generators to check quality
        _language_model (NGramLanguageModel): NGramLanguageModel instance
        _word_processor (WordProcessor): WordProcessor instance
    """

    def __init__(
        self, generators: dict, language_model: NGramLanguageModel, word_processor: WordProcessor
    ) -> None:
        """
        Initialize an instance of QualityChecker.

        Args:
            generators (dict): Dictionary in the form of {numeric type: generator}
            language_model (NGramLanguageModel):
                NGramLanguageModel instance to use for text generation
            word_processor (WordProcessor): WordProcessor instance to handle text processing
        """
        self._generators = generators
        self._language_model = language_model
        self._word_processor = word_processor

    def _calculate_perplexity(self, generated_text: str) -> float:  # type: ignore
        """
        Calculate perplexity for the text made by generator.

        Args:
            generated_text (str): Text made by generator

        Returns:
            float: Perplexity score for generated text

        Raises:
            ValueError: In case of inappropriate type input argument,
                or if input argument is empty,
                or if methods used return None,
                or if nothing was generated.
        """
        if not isinstance(generated_text, str) or not generated_text:
            raise ValueError('Trying to calculate perplexity with non-string or empty text')
        encoded = self._word_processor.encode(generated_text)
        if not encoded:
            raise ValueError('Encoded returned None')
        n_gram_size = self._language_model.get_n_gram_size()
        sum_log_prob = 0.0
        for index in range(n_gram_size - 1, len(encoded)):
            context = tuple(encoded[index - n_gram_size + 1: index])
            token = encoded[index]
            generated_tokens = self._language_model.generate_next_token(context)
            if not generated_tokens:
                raise ValueError('Next token was not generated')
            prob = generated_tokens.get(token)
            if prob:
                sum_log_prob += math.log(prob)
        if not sum_log_prob:
            raise ValueError('sum_log_prob was not counted')
        perplexity = math.exp(-sum_log_prob / (len(encoded) - n_gram_size))
        return perplexity

    def run(self, seq_len: int, prompt: str) -> list[GenerationResultDTO]:  # type: ignore
        """
        Check the quality of generators.

        Args:
            seq_len (int): Number of tokens to generate
            prompt (str): Beginning of the sequence

        Returns:
            list[GenerationResultDTO]:
                List of GenerationResultDTO instances in ascending order of perplexity score

        Raises:
            ValueError: In case of inappropriate type input arguments,
                or if input arguments are empty,
                or if sequence has inappropriate length,
                or if methods used return None.
        """
        if (not isinstance(seq_len, int) or not seq_len >= 1
                or not isinstance(prompt, str) or not prompt):
            raise ValueError('Trying to run with bad seq_len or prompt')
        results = []
        for gen_type, generator in self._generators.items():
            text = generator.run(seq_len=seq_len, prompt=prompt)
            if not text:
                raise ValueError('Text was not generated')
            perplexity = self._calculate_perplexity(text)
            if not perplexity:
                raise ValueError('Perplexity was not counted')
            results.append(GenerationResultDTO(text, perplexity, gen_type))
        return sorted(results, key=lambda x: (x.get_perplexity(), x.get_type()))


class Examiner:
    """
    A class that conducts an exam.

    Attributes:
        _json_path (str): Local path to assets file
        _questions_and_answers (dict[tuple[str, int], str]):
            Dictionary in the form of {(question, position of the word to be filled), answer}
    """

    def __init__(self, json_path: str) -> None:
        """
        Initialize an instance of Examiner.

        Args:
            json_path (str): Local path to assets file
        """
        self._json_path = json_path
        self._questions_and_answers = self._load_from_json()

    def _load_from_json(self) -> dict[tuple[str, int], str]:  # type: ignore
        """
        Load questions and answers from JSON file.

        Returns:
            dict[tuple[str, int], str]:
                Dictionary in the form of {(question, position of the word to be filled), answer}

        Raises:
            ValueError: In case of inappropriate type of attribute _json_path,
                or if attribute _json_path is empty,
                or if attribute _json_path has inappropriate extension,
                or if inappropriate type loaded data.
        """
        if not isinstance(self._json_path, str) or not self._json_path:
            raise ValueError
        with open(self._json_path, 'r', encoding='utf-8') as file:
            ques_ans = json.load(file)
        if not isinstance(ques_ans, list):
            raise ValueError('Questions and answers were not loaded')
        self._questions_and_answers = {(qu_an['question'], qu_an['location']): qu_an['answer']
                                       for qu_an in ques_ans}
        return self._questions_and_answers

    def provide_questions(self) -> list[tuple[str, int]]:  # type: ignore
        """
        Provide questions for an exam.

        Returns:
            list[tuple[str, int]]:
                List in the form of [(question, position of the word to be filled)]
        """
        return list(self._questions_and_answers.keys())

    def assess_exam(self, answers: dict[str, str]) -> float:  # type: ignore
        """
        Assess an exam by counting accuracy.

        Args:
            answers(dict[str, str]): Dictionary in the form of {question: answer}

        Returns:
            float: Accuracy score

        Raises:
            ValueError: In case of inappropriate type input argument or if input argument is empty.
        """
        if not isinstance(answers, dict) or not answers:
            raise ValueError('Trying to asses non-dict or empty answers')
        right_ans = {key[0]: value for key, value in self._questions_and_answers.items()}
        cor_ans = 0
        for ques in answers:
            if answers[ques].lower() == right_ans[ques].lower():
                cor_ans += 1
        return cor_ans / len(answers)


class GeneratorRuleStudent:
    """
    Base class for students generators.
    """

    _generator: GreedyTextGenerator | TopPGenerator | BeamSearchTextGenerator
    _generator_type: int

    def __init__(
        self, generator_type: int, language_model: NGramLanguageModel, word_processor: WordProcessor
    ) -> None:
        """
        Initialize an instance of GeneratorRuleStudent.

        Args:
            generator_type (int): Numeric type of the generator
            language_model (NGramLanguageModel):
                NGramLanguageModel instance to use for text generation
            word_processor (WordProcessor): WordProcessor instance to handle text processing
        """
        self._generator_type = generator_type
        generators = (GreedyTextGenerator(language_model, word_processor),
                TopPGenerator(language_model, word_processor, 0.5),
                BeamSearchTextGenerator(language_model, word_processor, 5))
        self._generator = generators[self._generator_type]

    def take_exam(self, tasks: list[tuple[str, int]]) -> dict[str, str]:  # type: ignore
        """
        Take an exam.

        Args:
            tasks (list[tuple[str, int]]):
                List with questions in the form of [(question, position of the word to be filled)]

        Returns:
            dict[str, str]: Dictionary in the form of {question: answer}

        Raises:
            ValueError: In case of inappropriate type input argument,
                or if input argument is empty,
                or if methods used return None.
        """
        if not isinstance(tasks, list) or not tasks:
            raise ValueError('Trying to take exam with non-list or empty tasks')
        answers = {}
        for (question, location) in tasks:
            context = question[:location]
            answer = self._generator.run(seq_len=1, prompt=context)
            if not answer:
                raise ValueError('Answer was not returned')
            if answer[-1] == '.':
                answer = f"{answer[:-1]} "
            answers[question] = f'{answer}{question[location:]}'
        return answers

    def get_generator_type(self) -> str:  # type: ignore
        """
        Retrieve generator type.

        Returns:
            str: Generator type
        """
        return GeneratorTypes().get_conversion_generator_type(self._generator_type)
