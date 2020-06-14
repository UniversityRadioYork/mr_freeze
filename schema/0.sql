BEGIN;

CREATE SCHEMA listens;

CREATE TABLE listens.listen (
  listen_id BIGSERIAL,
  mount TEXT,
  client_id TEXT,
  ip_address INET,
  user_agent TEXT,
  time_start TIMESTAMPTZ,
  time_end TIMESTAMPTZ NULL
);

COMMIT;