import numpy as np
from keras.src.legacy.preprocessing.image import ImageDataGenerator
from tensorflow.keras.preprocessing import image
from tensorflow.keras.models import load_model

# Load your trained model
model = load_model('chicken_breed_classifier.h5')

# Load and preprocess the input image
img_path = 'test/easter-egger.JPG'  # Replace with the image path you want to predict
img = image.load_img(img_path, target_size=(224, 224))  # Ensure the image is the correct size
img_array = image.img_to_array(img)
img_array = np.expand_dims(img_array, axis=0)  # Add batch dimension
img_array /= 255.0  # Normalize image (if your model was trained with this step)

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

# Get the top 3 predictions with their confidence
top_3_indexes = np.argsort(predictions[0])[::-1][:3]  # Get indexes of the top 3 predictions
top_3_confidences = predictions[0][top_3_indexes] * 100  # Multiply by 100 to get percentage
top_3_breeds = [list(train_generator.class_indices.keys())[index] for index in top_3_indexes]

# Print the top 3 predicted breeds and their confidence
for breed, confidence in zip(top_3_breeds, top_3_confidences):
    print(f"Predicted breed: {breed}, Confidence: {confidence:.2f}%")