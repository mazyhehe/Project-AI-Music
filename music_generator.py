# -*- coding: utf-8 -*-
"""Music Generator.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1RpUKuNORDJ2W28nzp4T5mEXGdWSz35RV
"""

!pip install tensorflow
!pip install music21

import os
import numpy as np
from music21 import converter, note, chord, pitch, stream
from keras.models import Sequential
from keras.layers import LSTM, Dense
from keras.utils import to_categorical

class MusicGenerator:
    def __init__(self, dataset_path, output_file, seq_length=100):
        """
        Initializes the MusicGenerator.
        :param dataset_path: Path to the directory containing MIDI files.
        :param output_file: Path for the output MIDI file.
        :param seq_length: Length of the input sequences for the LSTM model.
        """
        self.dataset_path = dataset_path
        self.output_file = output_file
        self.seq_length = seq_length
        self.model = None
        self.note_to_int = {}
        self.int_to_note = {}
        self.vocab_size = 0

    def load_midi_files(self):
        """
        Loads MIDI files from the dataset directory.
        :return: List of parsed MIDI files.
        """
        midi_files = []
        for root, _, files in os.walk(self.dataset_path):
            for file in files:
                if file.endswith('.midi') or file.endswith('.mid'):
                    midi_files.append(converter.parse(os.path.join(root, file)))
        return midi_files

    def preprocess_midi_files(self, midi_files):
        """
        Extracts notes and chords from MIDI files and converts them to a string representation.
        :param midi_files: List of parsed MIDI files.
        :return: List of notes and chords.
        """
        notes = []
        for midi_file in midi_files:
            for element in midi_file.flat.notesAndRests:
                if isinstance(element, note.Note):
                    notes.append(str(element.pitch))
                elif isinstance(element, chord.Chord):
                    notes.append('.'.join(str(n) for n in element.normalOrder))
        return notes

    def prepare_sequences(self, notes):
        """
        Prepares input and output sequences for the LSTM model.
        :param notes: List of notes and chords.
        :return: Tuple of input sequences (X_data) and output sequences (y_data).
        """
        note_to_int = {note: i for i, note in enumerate(sorted(set(notes)))}
        int_to_note = {i: note for note, i in note_to_int.items()}
        self.note_to_int = note_to_int
        self.int_to_note = int_to_note
        self.vocab_size = len(note_to_int)

        encoded_notes = [note_to_int[note] for note in notes]
        X_data, y_data = [], []
        for i in range(len(encoded_notes) - self.seq_length):
            sequence_in = encoded_notes[i:i + self.seq_length]
            sequence_out = encoded_notes[i + self.seq_length]
            X_data.append(np.eye(self.vocab_size)[sequence_in])
            y_data.append(sequence_out)

        return np.array(X_data), np.array(y_data)

    def build_model(self):
        """
        Builds the LSTM model.
        """
        model = Sequential([
            LSTM(256, input_shape=(self.seq_length, self.vocab_size), return_sequences=False),
            Dense(self.vocab_size, activation='softmax')
        ])
        model.compile(loss='categorical_crossentropy', optimizer='adam')
        self.model = model

    def train_model(self, X_data, y_data, epochs=50, batch_size=128):
        """
        Trains the LSTM model.
        :param X_data: Input sequences.
        :param y_data: Output sequences.
        :param epochs: Number of epochs for training.
        :param batch_size: Batch size for training.
        """
        y_data_one_hot = to_categorical(y_data, num_classes=self.vocab_size)
        self.model.fit(X_data, y_data_one_hot, batch_size=batch_size, epochs=epochs, validation_split=0.2)

    def generate_music(self, seed_sequence, num_steps=100):
        """
        Generates a sequence of notes using the trained model.
        :param seed_sequence: Seed sequence to start the generation.
        :param num_steps: Number of notes to generate.
        :return: List of generated notes.
        """
        generated_sequence = [self.int_to_note[np.argmax(note_vector)] for note_vector in seed_sequence]
        one_hot_sequence = [note_vector for note_vector in seed_sequence]

        for _ in range(num_steps):
            input_sequence = np.array(one_hot_sequence[-self.seq_length:])
            prediction = self.model.predict(input_sequence.reshape(1, self.seq_length, self.vocab_size))
            predicted_note_index = np.argmax(prediction)
            predicted_note = self.int_to_note[predicted_note_index]
            generated_sequence.append(predicted_note)
            one_hot_sequence.append(np.eye(self.vocab_size)[predicted_note_index])

        return generated_sequence

    def create_midi_from_notes(self, notes, output_file='generated_music.mid'):
        """
        Creates a MIDI file from a sequence of notes.
        :param notes: List of notes.
        :param output_file: Path for the output MIDI file.
        """
        generated_stream = stream.Stream()
        for n in notes:
            if n and not n.isdigit():
                try:
                    if '.' in n:
                        chord_notes = n.split('.')
                        chord_notes = [pitch.Pitch(midi=(int(cn) + 60)).nameWithOctave for cn in chord_notes]
                        generated_stream.append(chord.Chord(chord_notes))
                    else:
                        generated_stream.append(note.Note(n))
                except Exception as e:
                    print(f"Error processing note or chord {n}: {e}")
        generated_stream.write('midi', fp=output_file)

# Usage
if __name__ == "__main__":
    dataset_path = 'MusicTest'
    output_file = 'maestro_notes_and_chords.txt'

    music_generator = MusicGenerator(dataset_path, output_file)
    midi_files = music_generator.load_midi_files()
    notes = music_generator.preprocess_midi_files(midi_files)
    X_data, y_data = music_generator.prepare_sequences(notes)
    music_generator.build_model()
    music_generator.train_model(X_data, y_data)
    seed_sequence = X_data[0]
    generated_notes = music_generator.generate_music(seed_sequence)
    print("Generated sequence of notes:")
    print(generated_notes)
    music_generator.create_midi_from_notes(generated_notes)