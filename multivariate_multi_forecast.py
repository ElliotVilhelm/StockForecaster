from market import EquityData
from models.lstm import split, split_multivariate, show_plot, create_time_steps
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from utils import plot_train_history, multi_step_plot
from technical_analysis import moving_average


tf.random.set_seed(42)

BATCH_SIZE = 128
BUFFER_SIZE = 10000
EPOCHS = 15
step = 1
history_size = 30
target_distance = 1

features_considered = ['Close', 'Volume', 'MA_short', 'MA_long', 'Wilders_EMA']
e = EquityData('data/SPY.csv', 'SPY')
e.data['MA_short'] = moving_average(e, window=21)
e.data['MA_long'] = moving_average(e, window=5)
e.data['Wilders_EMA'] = e.close().ewm(alpha=1/15, adjust=False).mean()
e.data = e.data[21:]
EVALUATION_INTERVAL = int(e.data.shape[0]/BATCH_SIZE) * 1
features = e.data[features_considered]
assert(list(features)[0] == 'Close')
features.index = e.date()

features.plot(subplots=True)
plt.show()

dataset = features.values
x_train_multi, y_train_multi, x_val_multi, y_val_multi = split_multivariate(dataset, history_size, target_distance, step, single_step=False)

print ('Single window of past history : {}'.format(x_train_multi[0].shape))
print ('\n Target temperature to predict : {}'.format(y_train_multi[0].shape))

train_data_multi = tf.data.Dataset.from_tensor_slices((x_train_multi, y_train_multi))
train_data_multi = train_data_multi.cache().shuffle(BUFFER_SIZE).batch(BATCH_SIZE).repeat()

val_data_multi = tf.data.Dataset.from_tensor_slices((x_val_multi, y_val_multi))
val_data_multi = val_data_multi.batch(BATCH_SIZE).repeat()



multi_step_model = tf.keras.models.Sequential()
multi_step_model.add(tf.keras.layers.LSTM(16,
                                          return_sequences=True,
                                          input_shape=x_train_multi.shape[-2:]))
multi_step_model.add(tf.keras.layers.LSTM(4, activation='relu'))
multi_step_model.add(tf.keras.layers.Dense(target_distance))

multi_step_model.compile(optimizer=tf.keras.optimizers.RMSprop(clipvalue=1.0), loss='mae')


val_callback = tf.keras.callbacks.ModelCheckpoint(
    'checkpoints/multivariate_multi_model', monitor='val_loss', verbose=0, save_best_only=True,
    save_weights_only=False, mode='auto', save_freq='epoch'
)

multi_step_history = multi_step_model.fit(train_data_multi, epochs=EPOCHS,
                                          steps_per_epoch=EVALUATION_INTERVAL,
                                          validation_data=val_data_multi,
                                          validation_steps=50, callbacks=[val_callback])

# plot_train_history(multi_step_history, 'Multi-Step Training and validation loss')

for x, y in val_data_multi.take(5):
  multi_step_plot(x[0], y[0], multi_step_model.predict(x)[0], step).show()

multi_step_model.save('saved_models/multivariate_multi_model')