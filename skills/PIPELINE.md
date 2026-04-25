# skills/PIPELINE.md

## Goal
LangGraph state machine. Production pipeline (Agents 1-10) + Learning loop (Agents 11-13).

## Production Graph Structure
```python
StateGraph(ReelPipelineState)
  entry: trend_research
  edges (linear): trend_research → orchestrate → type_selector → clip_selection
               → script → edit_spec → caption → qa
  conditional after qa:
    if approved → publish → END
    if failed and revision_count < 3 → qa_revision_router
    if failed and revision_count >= 3 → END (with human_review=True flag)
  qa_revision_router → routes to: script | edit_spec | caption | clip_selection
```

## ReelPipelineState (TypedDict)
Required fields:
- account_niche, last_30_days_stats, last_10_reel_types, video_url (inputs)
- trend_brief, reel_brief, typed_spec, selected_clips, storyboard, edit_manifest, caption_package, qa_report (intermediate — each agent writes one)
- post_metadata, pipeline_status, qa_revision_count, error (control flow)

## Learning Loop (separate, async)
```python
# Called AFTER successful publish
def schedule_learning_checkpoints(post_id: str, post_time: datetime):
    for checkpoint, delta in [("T+1h", 1h), ("T+24h", 24h), ("T+7d", 7d), ("T+30d", 30d)]:
        scheduler.add_job(
            func=run_checkpoint,
            trigger="date",
            run_date=post_time + delta,
            args=[post_id, checkpoint],
            id=f"{post_id}_{checkpoint}",
        )
```

APScheduler uses SQLAlchemy jobstore backed by Supabase — jobs survive Railway restarts.

## run_checkpoint(post_id, checkpoint)
- T+1h: Agent 11 only → update hook_library
- T+24h: Agent 11 + Agent 13 → update clip_performance, hashtag_velocity
- T+7d: Agent 11 + 12 + 13 → full learning cycle
- T+30d: Agent 11 + 12 + 13 → full learning cycle + monthly audit

## Entry Point
```python
# src/scripts/run_reel.py
def main(dry_run=False):
    graph = build_production_graph()
    state = graph.invoke(initial_state)
    if state["pipeline_status"] == "published" and not dry_run:
        schedule_learning_checkpoints(state["post_metadata"]["post_id"], datetime.utcnow())
```
