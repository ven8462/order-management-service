#!/bin/sh
set -e

host="$1"
shift
cmd="$@"

echo "Waiting for Kafka at $host:9092..."
until nc -z $host 9092; do
  >&2 echo "Kafka is unavailable - sleeping"
  sleep 3
done

>&2 echo "Kafka is up - running tests"
exec $cmd