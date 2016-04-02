-- Table: "Segment"

-- DROP TABLE "Segment";

CREATE TABLE "Segment"
(
  seg_id bigint NOT NULL,
  act_type character varying(50),
  ath_cnt bigint,
  cat bigint,
  date_created timestamp without time zone,
  distance double precision,
  effort_cnt bigint,
  elev_gain double precision,
  elev_high double precision,
  elev_low double precision,
  name character varying(300),
  seg_points character varying,
  start_point geometry,
  end_point geometry,
  CONSTRAINT seg_id_pk PRIMARY KEY (seg_id)
)
WITH (
  OIDS=FALSE
);
ALTER TABLE "Segment"
  OWNER TO admin;

-- Index: "seg_Name_and_props"

-- DROP INDEX "seg_Name_and_props";

CREATE INDEX "seg_Name_and_props"
  ON "Segment"
  USING btree
  (name COLLATE pg_catalog."default", date_created, distance, cat, elev_gain, act_type COLLATE pg_catalog."default");

-- Index: start_end_locs

-- DROP INDEX start_end_locs;

CREATE INDEX start_end_locs
  ON "Segment"
  USING gist
  (start_point, end_point);

