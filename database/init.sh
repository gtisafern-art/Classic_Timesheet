#!/bin/bash
set -e

SQLCMD="/opt/mssql-tools18/bin/sqlcmd"
SERVER="mssql"
PASSWORD="$MSSQL_SA_PASSWORD"

echo "=== Initializing TimesheetDB ==="

echo "Running schema.sql..."
$SQLCMD -S "$SERVER" -U sa -P "$PASSWORD" -C -i /scripts/schema.sql

echo "Running seed.sql..."
$SQLCMD -S "$SERVER" -U sa -P "$PASSWORD" -C -i /scripts/seed.sql

echo "=== Done! Database is ready ==="
