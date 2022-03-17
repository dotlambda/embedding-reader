from embedding_reader import EmbeddingReader
import fire
import os
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
import fsspec
import math

def load_safety_model():
    """load the safety model"""
    import autokeras as ak  # pylint: disable=import-outside-toplevel
    from tensorflow.keras.models import load_model  # pylint: disable=import-outside-toplevel
    from os.path import expanduser  # pylint: disable=import-outside-toplevel

    home = expanduser("~")

    cache_folder = home + "/.cache/clip_retrieval"
    model_dir = cache_folder + "/clip_autokeras_binary_nsfw"
    if not os.path.exists(model_dir):
        os.makedirs(cache_folder, exist_ok=True)

        from urllib.request import urlretrieve  # pylint: disable=import-outside-toplevel

        path_to_zip_file = cache_folder + "/clip_autokeras_binary_nsfw.zip"
        url_model = (
            "https://raw.githubusercontent.com/LAION-AI/CLIP-based-NSFW-Detector/main/clip_autokeras_binary_nsfw.zip"
        )
        urlretrieve(url_model, path_to_zip_file)
        import zipfile  # pylint: disable=import-outside-toplevel

        with zipfile.ZipFile(path_to_zip_file, "r") as zip_ref:
            zip_ref.extractall(cache_folder)

    loaded_model = load_model(model_dir, custom_objects=ak.CUSTOM_OBJECTS)
    loaded_model.predict(np.random.rand(10 ** 3, 768).astype("float32"), batch_size=10 ** 3)

    return loaded_model


def main(input_folder, output_folder, batch_size=10**6, end=None):
    """main function"""
    reader = EmbeddingReader(input_folder)
    fs, relative_output_path = fsspec.core.url_to_fs(output_folder)
    fs.mkdirs(relative_output_path, exist_ok=True)

    model = load_safety_model()

    total = reader.count
    batch_count = math.ceil(total // batch_size)
    padding = int(math.log10(batch_count)) + 1

    for i, (embeddings, ids) in enumerate(reader(batch_size=batch_size, start=0, end=end)):
        predictions = model.predict(embeddings, batch_size=embeddings.shape[0])
        batch = np.hstack(predictions)
        padded_id = str(i).zfill(padding)
        output_file_path = os.path.join(relative_output_path, padded_id + ".npy")
        with fs.open(output_file_path, "wb") as f:
            np.save(f, batch)


if __name__ == '__main__':
    fire.Fire(main)
