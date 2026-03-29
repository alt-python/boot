-- V2: Add priority column
ALTER TABLE notes ADD COLUMN priority INTEGER NOT NULL DEFAULT 0;
