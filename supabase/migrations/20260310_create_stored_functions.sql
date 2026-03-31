-- ==========================================================================
-- Stored functions: assign_and_return_matches, update_topic_recency_metrics
-- ==========================================================================

-- -------------------------------------------------------------------------
-- assign_and_return_matches(dist_threshold FLOAT)
--
-- Links every raw_idea that has no topic yet to any topic whose
-- summary_embedding is within dist_threshold (cosine distance).
-- Returns the newly linked ideas with their matched topics as JSON.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.assign_and_return_matches(dist_threshold FLOAT)
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
        WHERE NOT EXISTS (
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

-- -------------------------------------------------------------------------
-- update_topic_recency_metrics()
--
-- Recomputes lifetime_size, activity_7d, activity_30d, recency_strength,
-- and dominance for every topic based on its linked raw_ideas.
-- -------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.update_topic_recency_metrics()
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
        GROUP BY t.id
    )
    UPDATE public.topic t
    SET
        lifetime_size    = tm.lifetime_size,
        activity_7d      = COALESCE(tm.activity_7d,   0),
        activity_30d     = COALESCE(tm.activity_30d,  0),
        -- Double weight for the last 7 days; single weight for rest of the month
        recency_strength = (COALESCE(tm.activity_7d, 0) * 2.0)
                         + ((COALESCE(tm.activity_30d, 0) - COALESCE(tm.activity_7d, 0)) * 1.0),
        -- 30% historical gravity + 70% current active weight
        dominance        = (tm.lifetime_size * 0.3)
                         + (COALESCE(tm.activity_30d, 0) * 0.7)
    FROM topic_metrics tm
    WHERE t.id = tm.topic_id;
END;
$$;
