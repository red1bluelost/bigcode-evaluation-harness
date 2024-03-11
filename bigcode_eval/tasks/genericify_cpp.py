# TODO: Remove all TODO comments once the implementation is complete.
"""
Genericify C++
No paper exists
Evaluation of model ability to make C++ code generic and constrained.
Homepage: No homepage exists
"""

import json

from typing import Literal

import evaluate

from bigcode_eval.base import Task

_CITATION = """
No citation exists
"""


def create_all_tasks():
    # TODO
    return {
        f"genericify_cpp_{cpp_type}": create_task(cpp_type)
        for cpp_type in ["base", "sfinae", "concepts"]
    }


def create_task(cpp_type):
    class GenericifyCppTask(GenericifyCpp):
        def __init__(self):
            super().__init__(cpp_type)

    return GenericifyCppTask


class GenericifyCpp(Task):
    DATASET_PATH = "red1bluelost/dataset_genericify_cpp"
    DATASET_NAME = None

    def __init__(self, cpp_type: Literal["base", "sfinae", "concepts"]):
        self.cpp_type = cpp_type
        super().__init__(
            # TODO: Specify the list of stop words in `stop_words` for the code generation task \
            # and if the evaluation requires executing the generated code in `requires_execution`.
            stop_words=[],
            requires_execution=True,
        )

    def get_dataset(self):
        """Returns dataset for the task or an iterable of any object, that get_prompt can handle"""
        return self.dataset["test"]

    def get_prompt(self, doc):
        """
        Builds the prompt for the LM to generate from.
        :param doc: dict[str: str]
            sample from the test dataset
        :return: str
        """
        instruction: str
        starter_code: str
        if self.cpp_type == "base":
            instruction = doc["base_prompt"]
            starter_code = doc["starter_code"]
        elif self.cpp_type == "sfinae":
            instruction = doc["sfinae_prompt"]
            starter_code = doc["base_canonical_solution"]
        elif self.cpp_type == "concepts":
            instruction = doc["concepts_prompt"]
            starter_code = doc["base_canonical_solution"]
        else:
            raise ValueError(f"Unsupported C++ type: {self.cpp_type}")

        context = "Ensure your response is valid C++ code. Do not include anything other than you rewrite of the function."
        prompt = context + "\n" + instruction.strip() + "\n\n" + starter_code.strip()
        return prompt.strip()

    def get_reference(self, doc, get_solution=False):
        """
        Builds the reference solution for the doc (sample from the test dataset).
        :param doc: dict[str: str]
            sample from the test dataset
        :return: str
        """
        if not get_solution:
            return {"tests": doc["tests"], "invalids": doc["invalids"]}

        if self.cpp_type == "base":
            return doc["base_canonical_solution"]
        if self.cpp_type == "sfinae":
            return doc["sfinae_canonical_solution"]
        if self.cpp_type == "concepts":
            return doc["concepts_canonical_solution"]
        raise ValueError(f"Unsupported C++ type: {self.cpp_type}")

    def postprocess_generation(self, generation, idx):
        # TODO: define the postprocessing for the LM generation
        """
        Defines the postprocessing for a LM generation.
        :param generation: str
            code generation from LM
        :param idx: int (if needed)
            index of doc in the dataset to which the generation belongs
        :return: str
        """
        doc = self.get_dataset()[idx]
        prompt = self.get_prompt(doc)
        gen = generation[len(prompt):]
        return gen

    def check_fn(self, code):
        """
        Checks whether the generated code is finished.
        Problem: Models rarely split their code into multiple functions, but this stops the model after the 1st function.
        Inspiration: https://github.com/THUDM/CodeGeeX/blob/23ee51505a2bcd34d59d2e271b22e5bd91475462/codegeex/benchmark/utils.py#L115
        """
        done = 2
        count = 0
        for c in code:
            if c == '{':
                count += 1
                continue
            elif c != '}':
                continue
            count -= 1
            if count == 0:
                done -= 1
                if done == 0:
                    return True
        return False

    def process_results(self, generations, references):
        """
        Takes the list of LM generations and evaluates them against ground truth references,
        returning the metric for the generations as in {"metric_name": result}.
        We encourage to directly load the metric from `evaluate` library to keep the code concise.
        :param generations: list(list(str))
            list of lists containing generations
        :param references: list(str)
            list of str containing refrences
        :return: dict[str: float]
        """
        code_metric = evaluate.load("red1bluelost/evaluate_genericify_cpp")

        # Remove main in case present
        generations = [
            [("\n" + g.split("int main")[0]).strip() for g in gen]
            for gen in generations
        ]

        ### EVALUATION ###
        results, logs = code_metric.compute(
            references=references,
            predictions=generations,
            cpp_type=self.cpp_type,
        )
        # Write logs to json
        with open("logs.json", "w") as f:
            json.dump(logs, f, indent=4, ensure_ascii=False)

        """Debugging help
        for i, (gen, ref) in enumerate(zip(generations, references)):
            import time
            starttime = time.time()            
            results, log = code_metric.compute(
                references=[ref],
                predictions=[gen],
                language=language,
                timeout=timeout,
            )
            print("Took: ", time.time() - starttime)
            with open("errors.txt", "a") as f:
                f.write(log[0][0][1]["result"] + "\n")
            if ("compilation error" in log[0][0][1]["result"]):
                print("Result")
                print(results)
                print("Log")
                print(log)
                print("Gen")
                print(gen[0])
                print("Ref")
                print(ref)
        """
        return results
