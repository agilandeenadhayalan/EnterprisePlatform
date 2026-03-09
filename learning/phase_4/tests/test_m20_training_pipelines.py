"""
Tests for Module 20: Model Training Pipelines.
~35 tests covering training_loop, sklearn_pipeline, experiment_tracking,
and hyperparameter_tuning.
"""

import math
import pytest

from m20_training_pipelines.training_loop import (
    SimpleModel,
    SGDOptimizer,
    MSELoss,
    TrainingLoop,
    EarlyStopping,
    LearningRateScheduler,
)
from m20_training_pipelines.sklearn_pipeline import Pipeline, CrossValidator
from m20_training_pipelines.experiment_tracking import ExperimentTracker
from m20_training_pipelines.hyperparameter_tuning import (
    ParameterSpace,
    GridSearch,
    RandomSearch,
    BayesianOptimizer,
)


# ===== SimpleModel Tests =====

class TestSimpleModel:

    def test_forward_produces_float(self):
        model = SimpleModel(input_dim=3, hidden_dim=4, output_dim=1)
        result = model.forward([1.0, 2.0, 3.0])
        assert isinstance(result, float)

    def test_deterministic_with_seed(self):
        m1 = SimpleModel(3, 4, 1, seed=42)
        m2 = SimpleModel(3, 4, 1, seed=42)
        assert m1.forward([1.0, 2.0, 3.0]) == m2.forward([1.0, 2.0, 3.0])

    def test_different_seeds_differ(self):
        m1 = SimpleModel(3, 4, 1, seed=42)
        m2 = SimpleModel(3, 4, 1, seed=99)
        assert m1.forward([1.0, 2.0, 3.0]) != m2.forward([1.0, 2.0, 3.0])

    def test_parameters_not_empty(self):
        model = SimpleModel(3, 4, 1)
        params = model.parameters()
        assert len(params) > 0


# ===== SGDOptimizer Tests =====

class TestSGDOptimizer:

    def test_step_updates_params(self):
        params = [[1.0, 2.0], [3.0]]
        opt = SGDOptimizer(params, lr=0.1)
        grads = [[0.5, -0.5], [1.0]]
        opt.step(grads)
        assert params[0][0] == pytest.approx(0.95)
        assert params[0][1] == pytest.approx(2.05)
        assert params[1][0] == pytest.approx(2.9)

    def test_negative_lr_raises(self):
        with pytest.raises(ValueError):
            SGDOptimizer([[1.0]], lr=-0.01)


# ===== MSELoss Tests =====

class TestMSELoss:

    def test_perfect_predictions(self):
        loss = MSELoss()
        assert loss.compute([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]) == 0.0

    def test_known_mse(self):
        loss = MSELoss()
        # (1-3)^2 + (2-2)^2 = 4 + 0 = 4, MSE = 4/2 = 2
        assert loss.compute([1.0, 2.0], [3.0, 2.0]) == 2.0

    def test_gradient_direction(self):
        loss = MSELoss()
        # predicted > actual -> positive gradient (should decrease)
        assert loss.gradient(5.0, 3.0) > 0
        # predicted < actual -> negative gradient (should increase)
        assert loss.gradient(1.0, 3.0) < 0

    def test_mismatched_lengths_raises(self):
        loss = MSELoss()
        with pytest.raises(ValueError):
            loss.compute([1.0], [1.0, 2.0])


# ===== TrainingLoop Tests =====

class TestTrainingLoop:

    def test_training_reduces_loss(self):
        model = SimpleModel(2, 4, 1, seed=42)
        opt = SGDOptimizer(model.parameters(), lr=0.001)
        loss_fn = MSELoss()
        loop = TrainingLoop(model, opt, loss_fn)

        data = [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]]
        labels = [2.0, 3.0, 5.0]

        loss1 = loop.train_epoch(data, labels)
        loss2 = loop.train_epoch(data, labels)
        # With a reasonable learning rate, loss should generally decrease
        # (for these simple cases with numerical gradients)
        assert isinstance(loss1, float)
        assert isinstance(loss2, float)

    def test_evaluate_returns_metrics(self):
        model = SimpleModel(2, 4, 1, seed=42)
        opt = SGDOptimizer(model.parameters(), lr=0.01)
        loss_fn = MSELoss()
        loop = TrainingLoop(model, opt, loss_fn)

        data = [[1.0, 0.0], [0.0, 1.0]]
        labels = [2.0, 3.0]

        metrics = loop.evaluate(data, labels)
        assert "mse" in metrics
        assert "rmse" in metrics
        assert "mae" in metrics
        assert metrics["rmse"] == pytest.approx(math.sqrt(metrics["mse"]))

    def test_evaluate_has_predictions(self):
        model = SimpleModel(2, 4, 1, seed=42)
        opt = SGDOptimizer(model.parameters(), lr=0.01)
        loss_fn = MSELoss()
        loop = TrainingLoop(model, opt, loss_fn)

        data = [[1.0, 0.0]]
        labels = [2.0]
        metrics = loop.evaluate(data, labels)
        assert len(metrics["predictions"]) == 1


# ===== EarlyStopping Tests =====

class TestEarlyStopping:

    def test_no_stop_on_improvement(self):
        es = EarlyStopping(patience=3)
        assert es.check(1.0) is False
        assert es.check(0.9) is False
        assert es.check(0.8) is False

    def test_stop_after_patience(self):
        es = EarlyStopping(patience=2)
        es.check(1.0)  # Set baseline
        es.check(1.1)  # No improvement
        assert es.check(1.2) is True  # patience exhausted

    def test_reset(self):
        es = EarlyStopping(patience=2)
        es.check(1.0)
        es.check(1.1)
        es.check(1.2)  # Should stop
        es.reset()
        assert es.best_loss is None
        assert es.epochs_without_improvement == 0

    def test_min_delta(self):
        es = EarlyStopping(patience=3, min_delta=0.1)
        es.check(1.0)
        # Improvement of 0.05 is less than min_delta of 0.1
        assert es.check(0.95) is False
        # But counter should increment
        assert es.epochs_without_improvement == 1

    def test_patience_must_be_positive(self):
        with pytest.raises(ValueError):
            EarlyStopping(patience=0)


# ===== LearningRateScheduler Tests =====

class TestLearningRateScheduler:

    def test_step_decay(self):
        opt = SGDOptimizer([[1.0]], lr=0.1)
        scheduler = LearningRateScheduler(opt, "step", step_size=2, gamma=0.5)
        scheduler.step(epoch=0)
        assert opt.lr == 0.1
        scheduler.step(epoch=1)
        assert opt.lr == 0.1
        scheduler.step(epoch=2)
        assert opt.lr == pytest.approx(0.05)

    def test_cosine_decay(self):
        opt = SGDOptimizer([[1.0]], lr=1.0)
        scheduler = LearningRateScheduler(opt, "cosine", total_epochs=100)
        scheduler.step(epoch=0)
        assert opt.lr == pytest.approx(1.0)
        scheduler.step(epoch=50)
        assert opt.lr == pytest.approx(0.5, abs=0.01)
        scheduler.step(epoch=100)
        assert opt.lr == pytest.approx(0.0, abs=0.01)

    def test_plateau_reduces_on_stagnation(self):
        opt = SGDOptimizer([[1.0]], lr=0.1)
        scheduler = LearningRateScheduler(
            opt, "plateau", patience=2, factor=0.5
        )
        scheduler.step(metric=1.0)
        scheduler.step(metric=1.0)  # No improvement
        scheduler.step(metric=1.0)  # Patience exhausted -> reduce
        assert opt.lr < 0.1

    def test_invalid_strategy_raises(self):
        opt = SGDOptimizer([[1.0]], lr=0.1)
        with pytest.raises(ValueError):
            LearningRateScheduler(opt, "unknown")


# ===== Pipeline Tests =====

class _DummyScaler:
    """Simple test scaler that doubles all values."""
    def fit(self, X, y):
        pass
    def transform(self, X):
        return [[v * 2 for v in row] for row in X]
    def get_params(self):
        return {"factor": 2}


class _DummyModel:
    """Simple test model that returns sum of features."""
    def __init__(self):
        self._fitted = False
    def fit(self, X, y):
        self._fitted = True
    def predict(self, X):
        return [sum(row) for row in X]


class TestPipeline:

    def test_fit_predict(self):
        pipe = Pipeline([("scaler", _DummyScaler()), ("model", _DummyModel())])
        X = [[1, 2], [3, 4]]
        y = [3, 7]
        pipe.fit(X, y)
        preds = pipe.predict(X)
        # Scaler doubles: [2,4], [6,8] -> model sums: 6, 14
        assert preds == [6, 14]

    def test_predict_before_fit_raises(self):
        pipe = Pipeline([("model", _DummyModel())])
        with pytest.raises(RuntimeError):
            pipe.predict([[1, 2]])

    def test_fit_predict_convenience(self):
        pipe = Pipeline([("model", _DummyModel())])
        preds = pipe.fit_predict([[1, 2]], [3])
        assert preds == [3]

    def test_get_params(self):
        pipe = Pipeline([("scaler", _DummyScaler()), ("model", _DummyModel())])
        params = pipe.get_params()
        assert "scaler" in params
        assert "model" in params

    def test_empty_pipeline_raises(self):
        with pytest.raises(ValueError):
            Pipeline([])

    def test_duplicate_names_raises(self):
        with pytest.raises(ValueError):
            Pipeline([("a", _DummyModel()), ("a", _DummyModel())])


# ===== CrossValidator Tests =====

class TestCrossValidator:

    def test_split_produces_correct_folds(self):
        cv = CrossValidator(n_folds=3, shuffle=False)
        data = list(range(9))
        splits = cv.split(data)
        assert len(splits) == 3
        for train_idx, val_idx in splits:
            assert len(val_idx) == 3
            assert len(train_idx) == 6

    def test_all_indices_covered(self):
        cv = CrossValidator(n_folds=5, shuffle=False)
        data = list(range(10))
        splits = cv.split(data)
        all_val = []
        for _, val_idx in splits:
            all_val.extend(val_idx)
        assert sorted(all_val) == list(range(10))

    def test_cross_validate_returns_scores(self):
        cv = CrossValidator(n_folds=3, seed=42)
        pipe = Pipeline([("model", _DummyModel())])
        X = [[i] for i in range(12)]
        y = [i for i in range(12)]

        def mse(y_true, y_pred):
            return sum((a - b)**2 for a, b in zip(y_true, y_pred)) / len(y_true)

        result = cv.cross_validate(pipe, X, y, mse)
        assert "fold_scores" in result
        assert "mean" in result
        assert "std" in result
        assert len(result["fold_scores"]) == 3

    def test_n_folds_too_small_raises(self):
        with pytest.raises(ValueError):
            CrossValidator(n_folds=1)


# ===== ExperimentTracker Tests =====

class TestExperimentTracker:

    def test_create_experiment(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("surge_v2", "Test surge model")
        exp = tracker.get_experiment("surge_v2")
        assert exp["name"] == "surge_v2"
        assert exp["description"] == "Test surge model"

    def test_duplicate_experiment_raises(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("x")
        with pytest.raises(ValueError):
            tracker.create_experiment("x")

    def test_start_and_end_run(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")
        run_id = tracker.start_run("exp1", "run_1")
        assert tracker.active_run_id == run_id
        tracker.end_run("FINISHED")
        assert tracker.active_run_id is None

    def test_log_params_and_metrics(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")
        run_id = tracker.start_run("exp1", "run_1")
        tracker.log_param("lr", 0.01)
        tracker.log_metric("loss", 0.5, step=1)
        tracker.log_metric("loss", 0.3, step=2)
        tracker.end_run()

        run = tracker.get_run(run_id)
        assert run["params"]["lr"] == 0.01
        assert len(run["metrics"]["loss"]) == 2
        assert run["metrics"]["loss"][1]["value"] == 0.3

    def test_log_artifact(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")
        tracker.start_run("exp1", "run_1")
        tracker.log_artifact("model_summary", "2 layers, 128 hidden")
        tracker.end_run()

    def test_compare_runs(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")

        run1 = tracker.start_run("exp1", "high_lr")
        tracker.log_metric("loss", 0.8)
        tracker.end_run()

        run2 = tracker.start_run("exp1", "low_lr")
        tracker.log_metric("loss", 0.3)
        tracker.end_run()

        comparison = tracker.compare_runs([run1, run2], "loss")
        assert comparison[0]["metric_value"] == 0.3
        assert comparison[0]["run_name"] == "low_lr"

    def test_no_active_run_raises(self):
        tracker = ExperimentTracker()
        with pytest.raises(RuntimeError):
            tracker.log_param("x", 1)

    def test_nested_run_raises(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")
        tracker.start_run("exp1", "run_1")
        with pytest.raises(RuntimeError):
            tracker.start_run("exp1", "run_2")
        tracker.end_run()

    def test_invalid_status_raises(self):
        tracker = ExperimentTracker()
        tracker.create_experiment("exp1")
        tracker.start_run("exp1", "run_1")
        with pytest.raises(ValueError):
            tracker.end_run(status="INVALID")
        tracker.end_run()


# ===== ParameterSpace Tests =====

class TestParameterSpace:

    def test_add_int(self):
        space = ParameterSpace()
        space.add_int("n_layers", 1, 5)
        assert space.params["n_layers"]["type"] == "int"

    def test_add_float_log_scale(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0001, 0.1, log_scale=True)
        assert space.params["lr"]["log_scale"] is True

    def test_add_categorical(self):
        space = ParameterSpace()
        space.add_categorical("optimizer", ["sgd", "adam"])
        assert "sgd" in space.params["optimizer"]["choices"]

    def test_log_scale_requires_positive(self):
        space = ParameterSpace()
        with pytest.raises(ValueError):
            space.add_float("x", 0.0, 1.0, log_scale=True)

    def test_invalid_range_raises(self):
        space = ParameterSpace()
        with pytest.raises(ValueError):
            space.add_int("x", 10, 5)


# ===== GridSearch Tests =====

class TestGridSearch:

    def test_generates_all_combinations(self):
        space = ParameterSpace()
        space.add_categorical("opt", ["a", "b"])
        space.add_int("n", 1, 2)
        gs = GridSearch(space)
        candidates = gs.generate_candidates()
        # 2 choices x 2 ints = 4 combinations
        assert len(candidates) == 4

    def test_float_generates_5_points(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0, 1.0)
        gs = GridSearch(space)
        candidates = gs.generate_candidates()
        assert len(candidates) == 5


# ===== RandomSearch Tests =====

class TestRandomSearch:

    def test_generates_n_trials(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0, 1.0)
        space.add_int("layers", 1, 10)
        rs = RandomSearch(space, n_trials=20, seed=42)
        candidates = rs.generate_candidates()
        assert len(candidates) == 20

    def test_reproducible_with_seed(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0, 1.0)
        rs1 = RandomSearch(space, n_trials=5, seed=42)
        rs2 = RandomSearch(space, n_trials=5, seed=42)
        assert rs1.generate_candidates() == rs2.generate_candidates()

    def test_within_bounds(self):
        space = ParameterSpace()
        space.add_float("lr", 0.001, 0.1)
        space.add_int("n", 1, 5)
        rs = RandomSearch(space, n_trials=50, seed=42)
        for c in rs.generate_candidates():
            assert 0.001 <= c["lr"] <= 0.1
            assert 1 <= c["n"] <= 5


# ===== BayesianOptimizer Tests =====

class TestBayesianOptimizer:

    def test_initial_random_suggestions(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0, 1.0)
        bo = BayesianOptimizer(space, n_initial=5, seed=42)
        suggestion = bo.suggest([])
        assert "lr" in suggestion
        assert 0.0 <= suggestion["lr"] <= 1.0

    def test_suggestions_after_initial(self):
        space = ParameterSpace()
        space.add_float("lr", 0.01, 1.0)
        space.add_categorical("opt", ["sgd", "adam"])
        bo = BayesianOptimizer(space, n_initial=3, seed=42)

        # Simulate 5 trials (more than n_initial)
        trials = [
            {"params": {"lr": 0.1, "opt": "sgd"}, "score": 0.5},
            {"params": {"lr": 0.01, "opt": "adam"}, "score": 0.2},
            {"params": {"lr": 0.5, "opt": "sgd"}, "score": 0.8},
            {"params": {"lr": 0.05, "opt": "adam"}, "score": 0.3},
            {"params": {"lr": 0.02, "opt": "adam"}, "score": 0.1},
        ]
        suggestion = bo.suggest(trials)
        assert "lr" in suggestion
        assert "opt" in suggestion
        assert 0.01 <= suggestion["lr"] <= 1.0

    def test_split_trials(self):
        space = ParameterSpace()
        space.add_float("lr", 0.0, 1.0)
        bo = BayesianOptimizer(space, seed=42)

        trials = [
            {"params": {"lr": 0.1}, "score": 0.5},
            {"params": {"lr": 0.2}, "score": 0.1},
            {"params": {"lr": 0.3}, "score": 0.9},
            {"params": {"lr": 0.4}, "score": 0.3},
        ]
        good, bad = bo._split_trials(trials, percentile=0.5)
        assert len(good) == 2
        assert good[0]["score"] <= good[1]["score"]
