-- 1. Truncate tables to safely add NOT NULL constraints
-- Given the sweeping schema change to multi-tenancy, we truncate the existing single-tenant data.
TRUNCATE TABLE public.raw_idea CASCADE;
TRUNCATE TABLE public.topic CASCADE;
TRUNCATE TABLE public.trait CASCADE;
TRUNCATE TABLE public.chat_sessions CASCADE;

-- 2. Add user_id columns referencing public.users(auth_id)
ALTER TABLE public.raw_idea 
  ADD COLUMN user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE;

ALTER TABLE public.topic 
  ADD COLUMN user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE;

ALTER TABLE public.trait 
  ADD COLUMN user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE;

ALTER TABLE public.chat_sessions 
  ADD COLUMN user_id TEXT NOT NULL REFERENCES public.users(auth_id) ON DELETE CASCADE;

-- 3. Update assign_and_return_matches to strictly enforce user boundary
DROP FUNCTION IF EXISTS public.assign_and_return_matches(FLOAT);

CREATE OR REPLACE FUNCTION public.assign_and_return_matches(dist_threshold FLOAT, p_user_id TEXT)
RETURNS TABLE (
    idea_id     BIGINT,
    content     TEXT,
    topics      JSONB
)
LANGUAGE plpgsql AS
$$
BEGIN
    RETURN QUERY
    WITH new_links AS (
        INSERT INTO public.idea_topics AS new_it (idea_id, topic_id)
        SELECT i.id, t.id
        FROM public.raw_idea i
        CROSS JOIN public.topic t
        WHERE i.user_id = p_user_id 
          AND t.user_id = p_user_id
          AND NOT EXISTS (
            SELECT 1
            FROM public.idea_topics existing_it
            WHERE existing_it.idea_id = i.id
        )
          AND (i.embeddings <=> t.summary_embedding) < dist_threshold
        RETURNING new_it.idea_id, new_it.topic_id
    )
    SELECT
        i.id,
        i.content,
        jsonb_agg(
            jsonb_build_object(
                'id',         t.id,
                'title',      t.title,
                'similarity', (1 - (i.embeddings <=> t.summary_embedding))
            )
        )
    FROM new_links nl
    JOIN public.raw_idea i ON nl.idea_id = i.id
    JOIN public.topic    t ON nl.topic_id = t.id
    GROUP BY i.id, i.content;
END;
$$;

-- 4. Update topic recency metrics to scope to the specific user's topics
DROP FUNCTION IF EXISTS public.update_topic_recency_metrics();

CREATE OR REPLACE FUNCTION public.update_topic_recency_metrics(p_user_id TEXT)
RETURNS VOID
LANGUAGE plpgsql AS
$$
BEGIN
    WITH topic_metrics AS (
        SELECT
            t.id AS topic_id,
            COUNT(ri.id) AS lifetime_size,
            COUNT(ri.id) FILTER (WHERE ri.created_at >= NOW() - INTERVAL '7 days')  AS activity_7d,
            COUNT(ri.id) FILTER (WHERE ri.created_at >= NOW() - INTERVAL '30 days') AS activity_30d
        FROM public.topic t
        LEFT JOIN public.idea_topics it ON t.id = it.topic_id
        LEFT JOIN public.raw_idea    ri ON it.idea_id = ri.id
        WHERE t.user_id = p_user_id
        GROUP BY t.id
    )
    UPDATE public.topic t
    SET
        lifetime_size    = tm.lifetime_size,
        activity_7d      = COALESCE(tm.activity_7d,   0),
        activity_30d     = COALESCE(tm.activity_30d,  0),
        recency_strength = (COALESCE(tm.activity_7d, 0) * 2.0)
                         + ((COALESCE(tm.activity_30d, 0) - COALESCE(tm.activity_7d, 0)) * 1.0),
        dominance        = (tm.lifetime_size * 0.3)
                         + (COALESCE(tm.activity_30d, 0) * 0.7)
    FROM topic_metrics tm
    WHERE t.id = tm.topic_id;
END;
$$;
