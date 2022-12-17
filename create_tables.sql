CREATE TABLE IF NOT EXISTS public.account
(
    id serial NOT NULL,
    external_id character varying(100) NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.preferences
(
    id serial NOT NULL,
    age_from integer,
    age_to integer,
    sex_id integer,
    city_id character varying(300),
    marital_status integer,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.users
(
    id serial NOT NULL,
    is_banned boolean,
    preferences_id serial,
    account_id serial,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS public.relation
(
    id serial NOT NULL,
    reaction boolean,
    user_id serial NOT NULL,
    account_id serial NOT NULL,
    is_favorite boolean,
    PRIMARY KEY (id)
);

ALTER TABLE IF EXISTS public.users
    ADD FOREIGN KEY (preferences_id)
    REFERENCES public.preferences (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public.users
    ADD FOREIGN KEY (account_id)
    REFERENCES public.account (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public.relation
    ADD FOREIGN KEY (user_id)
    REFERENCES public.users (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public.relation
    ADD FOREIGN KEY (account_id)
    REFERENCES public.account (id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;

END;