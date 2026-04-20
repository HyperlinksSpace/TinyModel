# Phase 1 comparison matrix

| dataset | model | seed | max_train_samples | max_eval_samples | accuracy | macro_f1 | f1_Business | f1_Sci/Tech | f1_Sports | f1_World | f1_anger | f1_fear | f1_joy | f1_love | f1_sadness | f1_surprise |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ag_news | scratch | 42 | 120 | 80 | 0.2625 | 0.10396 | 0.0 | 0.0 | 0.415842 | 0.0 |  |  |  |  |  |  |
| ag_news | pretrained | 42 | 120 | 80 | 0.7125 | 0.604038 | 0.71875 | 0.0 | 0.954545 | 0.742857 |  |  |  |  |  |  |
| emotion | scratch | 42 | 120 | 80 | 0.2375 | 0.063973 |  |  |  |  | 0.0 | 0.0 | 0.0 | 0.0 | 0.383838 | 0.0 |
| emotion | pretrained | 42 | 120 | 80 | 0.25 | 0.075379 |  |  |  |  | 0.0 | 0.0 | 0.064516 | 0.0 | 0.387755 | 0.0 |
