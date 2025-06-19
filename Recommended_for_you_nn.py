import tensorflow as tf
from keras import layers, Model
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder, MinMaxScaler
from datetime import datetime
from sqlalchemy import create_engine
import joblib
from model import get_weather_from_api
import matplotlib.pyplot as plt
from keras.callbacks import EarlyStopping

# --- Model Definition ---
def create_model(user_vocab_size, interest_vocab_size, pincode_vocab_size, weather_vocab_size):
    user_input = layers.Input(shape=(1,), name='user_id')
    hour_input = layers.Input(shape=(1,), name='hour')
    day_input = layers.Input(shape=(1,), name='day_of_week')
    season_input = layers.Input(shape=(1,), name='season')
    weather_input = layers.Input(shape=(1,), name='weather')
    is_day_input = layers.Input(shape=(1,), name='is_day')
    lat_input = layers.Input(shape=(1,), name='latitude')
    lon_input = layers.Input(shape=(1,), name='longitude')
    interest_input = layers.Input(shape=(1,), name='last_interest')
    interest_emb = layers.Embedding(interest_vocab_size, 8)(interest_input)

    user_emb = layers.Embedding(user_vocab_size, 8)(user_input)
    weather_emb = layers.Embedding(weather_vocab_size, 4)(weather_input)

    x = layers.concatenate([
        layers.Flatten()(user_emb),
        layers.Flatten()(weather_emb),
        layers.Flatten()(interest_emb), 
        hour_input,
        day_input,
        season_input,
        is_day_input,
        lat_input,
        lon_input
    ])

    # Shared base
    x = layers.Dense(64, activation='relu')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Dropout(0.3)(x)
    x = layers.Dense(32, activation='relu')(x)

    # Interest branch
    i = layers.Dense(32, activation='relu')(x)
    interest_out = layers.Dense(interest_vocab_size, activation='softmax', name='interest_output')(i)

    # Pincode branch
    p = layers.Dense(32, activation='relu')(x)
    pincode_out = layers.Dense(pincode_vocab_size, activation='softmax', name='pincode_output')(p)

    model = Model(inputs=[user_input, hour_input, day_input, season_input, weather_input, is_day_input, lat_input, lon_input, interest_input],
                  outputs=[interest_out, pincode_out])

    # model.compile(optimizer='adam',
    #             loss='sparse_categorical_crossentropy',
    #             metrics={'interest_output': 'accuracy', 'pincode_output': 'accuracy'})

    # Compile the model with tuned loss weights
    model.compile(
        optimizer='adam',
        loss={'interest_output': 'sparse_categorical_crossentropy', 'pincode_output': 'sparse_categorical_crossentropy'},
        loss_weights={'interest_output': 1.5, 'pincode_output': 1.0},
        metrics={'interest_output': 'accuracy', 'pincode_output': 'accuracy'}
    )
    return model

# --- Database Setup ---
db_params = {
    'dbname': 'test',
    'user': 'postgres',
    'password': 'boathead',
    'host': 'localhost',
    'port': '5432'
}

def connect_to_db(params):
    conn_string = f"postgresql://{params['user']}:{params['password']}@{params['host']}:{params['port']}/{params['dbname']}"
    return create_engine(conn_string)

def load_data(engine):
    query = "SELECT * FROM user_interaction"
    df = pd.read_sql(query, engine)
    return df

# --- Feature Engineering ---
def extract_features(df):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['hour'] = df['timestamp'].dt.hour
    df['day_of_week'] = df['timestamp'].dt.dayofweek
    df['month'] = df['timestamp'].dt.month
    df['season'] = df['month'].map({12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1, 6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3})

    # Use already stored weather data
    df['weather'] = df['weather_condition']
    df['is_day'] = df['is_day'].astype(int)

    # Scale latitude and longitude
    lat_scaler = MinMaxScaler()
    lon_scaler = MinMaxScaler()

    df['lat_scaled'] = lat_scaler.fit_transform(df[['latitude']])
    df['lon_scaled'] = lon_scaler.fit_transform(df[['longitude']])

    joblib.dump(lat_scaler, 'lat_scaler.pkl')
    joblib.dump(lon_scaler, 'lon_scaler.pkl')

    return df

# --- Encode categorical variables ---
def encode_column(df, column):
    encoder = LabelEncoder()
    df[column + '_enc'] = encoder.fit_transform(df[column])
    return encoder

# --- Main training function ---
def train_model():
    engine = connect_to_db(db_params)
    df = load_data(engine)
    df = extract_features(df)

    user_encoder = encode_column(df, 'user_id')
    interest_encoder = encode_column(df, 'interest')
    pincode_encoder = encode_column(df, 'pincode')
    weather_encoder = encode_column(df, 'weather')

    model = create_model(
        user_vocab_size=len(user_encoder.classes_),
        interest_vocab_size=len(interest_encoder.classes_),
        pincode_vocab_size=len(pincode_encoder.classes_),
        weather_vocab_size=len(weather_encoder.classes_)
    )

    # Set up early stopping
    early_stop = EarlyStopping(
        monitor='val_loss',
        patience=5,
        min_delta=0.001,
        restore_best_weights=True
    )

    # Capture the training history
    history = model.fit(
        [
            df['user_id_enc'],
            df['hour'],
            df['day_of_week'],
            df['season'],
            df['weather_enc'],
            df['is_day'],
            df['lat_scaled'],
            df['lon_scaled'],
            df['interest_enc']
        ],
        [
            df['interest_enc'],
            df['pincode_enc']
        ],
        epochs=20,
        batch_size=32,
        validation_split=0.2,
        callbacks=[early_stop]
    )

    # Save the model
    model.save("recommender_model.keras")
    joblib.dump(user_encoder, 'user_encoder.pkl')
    joblib.dump(interest_encoder, 'interest_encoder.pkl')
    joblib.dump(pincode_encoder, 'pincode_encoder.pkl')
    joblib.dump(weather_encoder, 'weather_encoder.pkl')
    print("Model and encoders saved successfully.")

    # Plotting the accuracy
    plt.plot(history.history['interest_output_accuracy'], label='Interest Accuracy')
    plt.plot(history.history['pincode_output_accuracy'], label='Pincode Accuracy')
    plt.title("Accuracy over Epochs")
    plt.xlabel("Epoch")
    plt.ylabel("Accuracy")
    plt.legend()
    plt.show()

if __name__ == "__main__":
    train_model()
