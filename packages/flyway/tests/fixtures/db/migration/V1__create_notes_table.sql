-- V1: Create notes table
CREATE TABLE notes (
  id    INTEGER PRIMARY KEY,
  title TEXT    NOT NULL,
  body  TEXT,
  done  INTEGER NOT NULL DEFAULT 0
);
