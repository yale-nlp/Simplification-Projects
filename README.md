# simplification-project

Welcome to the simplification project repository! 
We aim to explore ways to train language models to simplify radiology reports to make them more accessible to laypeople.

### Set-up
To get started, clone this repository and set up a `simplification` environment as follows:
```
# Clone the repo
git clone https://github.com/ljyflores/simplification-project
cd simplification-project

# Set up the environment
conda create --name simplification python=3.8
conda activate simplification
pip install -r requirements.txt

# Set up pre-commit hooks
pre-commit install
```

We also create a new environment specifically for the <a href="https://github.com/ThomasScialom/QuestEval#text-simplification">QuestEval</a> evaluation metric, using the following steps:
```
# Create environment and install requirements
conda create --name questeval python=3.9
conda activate questeval
pip3 install torch torchvision torchaudio ipykernel jupyter ipywidgets

# Clone QuestEval and install
git clone https://github.com/ThomasScialom/QuestEval.git
cd QuestEval
pip install -e .
```

### Data

Each dataset is stored using `json` files – each with two versions: `<dataset>.json` and `<dataset>_multiple.json`. 
* `<dataset>.json` is used for training
  * one example input is mapped to exactly one training label – so if there are 10 labels written for one input, the `<dataset>.json` will have 10 examples for this input
* `<dataset>_multiple.json` is used for evaluation
  *  one example input is mapped to all the training labels written for it – so if there are 10 labels written for one input, the `<dataset>_multiple.json` will still only have 1 example for it

```
{
  "train": [
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
             ...,
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
            ],
  "test":  [
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
             ...,
             {"input": <str>,
             "labels": [<str>, <str>, ..., <str>]},
            ],
}
```

### Weights and Biases
Before training, be sure to log in to <a href="https://wandb.ai/">wandb</a> (weights and biases), which helps us log experiments and keep track of their performance. To do this, set up a (free) account with wandb, then copy the API key! Back in the terminal, we can log in as follows:
```
wandb login <API_KEY>
```

### Training

We've set up a script that reads in dataset from the `data` folder and trains a model with the specified parameters.
It then outputs a textfile of the summaries generated by the model for the `test` set, and places them in the `output` folder as `<dataset_name>.txt`.
Here's the structure of the command to train a model:
```
CUDA_VISIBLE_DEVICES=<gpu_id> WANDB_PROJECT=<wandb_project_name> nohup python train.py --dataset <dataset> --lr <lr> --epochs <num_epochs> --batch_size <batch_size> --gradient_accumulation_steps <grad_acc> --model <model> --weight_decay <weight_decay> >> <log_file_name>
```

For example,
```
CUDA_VISIBLE_DEVICES=7 WANDB_PROJECT=asset_flant5 nohup python train.py --dataset asset --lr 5e-4 --epochs 10 --batch_size 8 --gradient_accumulation_steps 8 --model flant5_base --weight_decay 0.05 >> nohup_asset_flant5_train.out
```

These are some notes on each of the parameters: 
* `wandb_project_name`: Name of project in weights and biases (wandb.ai) where the current experiments get logged to; be sure to use the same project name if you want the current experiment to get logged to a certain project
* `dataset`: One of `asset`, `asset_context_all`, `cochrane`, `cochrane_context_all`, `turkcorpus`, `turkcorpus_context_all`, `radiology_indiv`, `radiology_indiv_context_all`
* `model`: One of `bart`, `flant5` (FLAN Large), `flant5_base`
* `weight_decay`: Similar to dropout (0 is none)
* `batch_size` and `gradient_accumulation_steps`: Actual batch size is the product of `batch_size` and `gradient_accumulation_steps`, `batch_size` controls how many samples fit on the model, while `gradient_accumulation_steps` is the number of steps taken before backpropagating

### Parameters
| `model`       | `dataset`                              | `lr` | `num_epochs` | `batch_size` | `gradient_accumulation_steps` | `weight_decay` |
| ------------- | -------------------------------------- | ---- | ------------ | ------------ | ----------------------------- | -------------- |
| `flant5_base` | `asset`/`radiology_indiv`/`turkcorpus` | 5e-4 | 10           | 8            | 8                             | 0.05           |
| `flant5_base` | `cochrane`                             | 5e-4 | 10           | 2            | 32                            | 0.05           |
| `bart`        | `asset`/`radiology_indiv`/`turkcorpus` | 1e-5 | 10           | 8            | 8                             | 0.01           |
| `bart`        | `cochrane`                             | 1e-5 | 10           | 2            | 16                            | 0.01           |

### Evaluation

To run the evaluation script that compares the output `.txt` file to the reference summaries in the `.json` file, run this command:
```
CUDA_VISIBLE_DEVICES=<gpu_id> nohup python eval.py --dataset <dataset> --preds_path <model predictions> >> <log_file_name>
```
For example:
```
CUDA_VISIBLE_DEVICES=7 nohup python eval.py --dataset asset_context_all --preds_path output/asset_context_all_flant5.txt >> nohup_asset_context_all_flant5_eval.out
```

#### Metrics
To evaluate the model's performance, we use the following metrics:
* BERT-Score
* SARI
* ROUGE
* Flesch Reading Ease
* Flesch Kincaid Grade
* Dale Chall
* Gunning Fog
