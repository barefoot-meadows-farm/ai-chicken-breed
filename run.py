import numpy as np
from keras.src.legacy.preprocessing.image import ImageDataGenerator
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

#accept File from file upload
def predict_breed(image_file):
    # Load your trained model
    model = load_model('chicken_breed_classifier.h5')

    # Load and preprocess the input image
    img = image.load_img(image_file, target_size=(224, 224))  # Use file-like object directly
    img_array = image.img_to_array(img)
    img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
    img_array /= 255.0  # Normalize image

    # Predict the breed with the model
    predictions = model.predict(img_array)

    # Define your ImageDataGenerator (make sure it matches how you trained the model)
    train_datagen = ImageDataGenerator(rescale=1./255)  # Apply any transformations that match your training setup

    # Set up the generator for loading images from your dataset
    train_generator = train_datagen.flow_from_directory(
        'dataset/train',  # Path to your dataset
        target_size=(224, 224),  # Resize to match model input size
        batch_size=32,  # Define batch size
        class_mode='categorical'  # For multi-class classification
    )

    # Ensure the class indices are consistent
    class_indices = train_generator.class_indices
    breed_labels = list(class_indices.keys())

    # Get the top 3 predictions
    top_3_indexes = np.argsort(predictions[0])[::-1][:3]
    top_3_confidences = (predictions[0][top_3_indexes] * 100).tolist()  # Convert to list for JSON serialization
    top_3_breeds = [breed_labels[index] for index in top_3_indexes]

    # Build the results
    results = [{"breed": breed, "confidence": round(confidence, 2)} for breed, confidence in
               zip(top_3_breeds, top_3_confidences)]
    return results