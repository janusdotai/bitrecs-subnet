#!/usr/bin/env bash
sleep $(( RANDOM % 300 ))
set -e
cd $HOME/bt/bitrecs-subnet/

git fetch origin main

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
  echo "Updating to latest main"
  git pull --ff-only origin main
  pip install -e .
  pm2 restart 0
fi

