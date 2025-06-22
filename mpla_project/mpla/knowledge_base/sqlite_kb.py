import json
import aiosqlite
from datetime import datetime, timezone
from typing import List, Optional, TypeVar, Type, Dict, Any
import asyncio

from .schemas import (
    BaseMPLAModel, OriginalPrompt, PromptVersion, EvaluationResult, 
    IterationLog, TargetAIProfile, AIOutput, MetaPrompt
)
from .db_connector import KnowledgeBase, T # T is TypeVar('T', bound=BaseMPLAModel)

DATABASE_SCHEMA_VERSION = 2 # Incremented due to new table

# This is a copy of the constant from the enhancer, used ONLY for seeding.
# This avoids a potential circular import during database initialization.
_INITIAL_ARCHITECT_META_PROMPT = """
**Role:** You are a Prompt Architect AI.

**Objective:** Transform a given input prompt into a significantly more effective version, optimized for clarity, precision, and the ability to elicit high-quality responses from other AI systems.

**Input:** You will be provided with a single "Original Prompt" that requires enhancement.

**Process:**
1.  **Analyze Intent & Weaknesses:**
    *   Identify the core purpose and desired outcome of the Original Prompt.
    *   Critically diagnose ambiguities, vagueness, missing information, implicit assumptions, or structural flaws that could hinder an AI's performance.
2.  **Strategize Enhancements:**
    *   Determine necessary clarifications, contextual additions (e.g., background, constraints, illustrative examples), and structural improvements.
    *   Consider defining or refining a persona, tone, style, or specific output format for the AI that will ultimately process the enhanced prompt.
    *   **For requests involving comparisons, lists, or structured data, explicitly instruct the AI to format its output using markdown tables for optimal clarity.**
    *   Formulate changes to maximize the target AI's comprehension and minimize generic or off-target responses.
3.  **Construct Refined Prompt:**
    *   Create a new, "Enhanced Prompt." This prompt must be self-contained, precise, actionable, and ready for direct use with another AI system to achieve the original (but now clarified) intent.
4.  **Explain Rationale (Elucidation):**
    *   Provide a concise explanation detailing the key strategic changes made to the Original Prompt and the reasoning behind them. This explanation should highlight prompt engineering best practices demonstrated in the transformation.

**Output:**
Your response MUST STRICTLY contain ONLY the following two sections with their exact headings. Do not include any other text, conversation, introductions, or explanations before or after these sections.

**Enhanced Prompt:**
[The full text of the new, refined prompt]

**Elucidation:**
[Your full explanation of the changes made]
"""

class SQLiteKnowledgeBase(KnowledgeBase):
    """SQLite implementation of the KnowledgeBase.
    
    Handles persistent storage and retrieval of MPLA operational data using aiosqlite.
    """
    def __init__(self, db_path: str):
        """
        Initializes the SQLiteKnowledgeBase.

        Args:
            db_path (str): Path to the SQLite database file.
                           If ':memory:', an in-memory database is used.
        """
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        """Establishes connection to the SQLite database and creates tables if they don't exist."""
        if self._conn is None: 
            try:
                self._conn = await aiosqlite.connect(self.db_path)
                self._conn.row_factory = aiosqlite.Row 
                await self._create_tables()
                await self._seed_initial_metaprompt()
            except aiosqlite.Error as e:
                print(f"Failed to connect to SQLite DB at {self.db_path}: {e}")
                self._conn = None 
                raise 

    async def disconnect(self) -> None:
        """Closes the connection to the SQLite database."""
        if self._conn:
            try:
                await self._conn.close()
                # print(f"Disconnected from SQLite DB at {self.db_path}")
            except aiosqlite.Error as e:
                print(f"Error disconnecting from SQLite DB: {e}")
            finally:
                self._conn = None

    def _get_table_name(self, model_cls: Type[T]) -> str:
        """Maps a Pydantic model class to its corresponding database table name."""
        schema_map = {
            MetaPrompt: "meta_prompts",
            OriginalPrompt: "original_prompts",
            PromptVersion: "prompt_versions",
            TargetAIProfile: "target_ai_profiles",
            AIOutput: "ai_outputs",
            EvaluationResult: "evaluation_results",
            IterationLog: "iteration_logs"
        }
        return schema_map.get(model_cls, model_cls.__name__.lower() + "s")

    async def _create_tables(self) -> None:
        """Creates database tables if they do not already exist."""
        if not self._conn: 
            # This should ideally not happen if connect() is called first and handles its errors.
            # However, as a safeguard:
            # print("Warning: _create_tables called without an active connection. Attempting to connect.")
            await self.connect()
            if not self._conn: # Still no connection after attempt
                raise ConnectionError("Cannot create tables: Database connection not established.")

        async with self._conn.cursor() as cursor:
            await cursor.execute("PRAGMA foreign_keys = ON;")

            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS meta_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    template TEXT NOT NULL,
                    is_active BOOLEAN NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS original_prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    user_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS target_ai_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    api_endpoint TEXT,
                    capabilities_json TEXT, -- JSON list of strings
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS iteration_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_prompt_id INTEGER NOT NULL,
                    session_id TEXT NOT NULL,
                    iteration_number INTEGER NOT NULL,
                    active_prompt_version_id INTEGER, -- Nullable
                    ai_output_id INTEGER, -- Nullable
                    evaluation_result_id INTEGER, -- Nullable
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (original_prompt_id) REFERENCES original_prompts (id)
                    -- FKs to prompt_versions, ai_outputs, evaluation_results can be added if they always exist prior
                    -- For now, these are application-level links or updated post-creation.
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_prompt_id INTEGER,
                    iteration_id INTEGER, -- FK to iteration_logs
                    version_number INTEGER NOT NULL,
                    prompt_text TEXT NOT NULL,
                    enhancement_rationale TEXT,
                    target_ai_profile_id INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (original_prompt_id) REFERENCES original_prompts (id),
                    FOREIGN KEY (iteration_id) REFERENCES iteration_logs (id) ON DELETE SET NULL, -- Or CASCADE
                    FOREIGN KEY (target_ai_profile_id) REFERENCES target_ai_profiles (id)
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS ai_outputs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_version_id INTEGER NOT NULL,
                    raw_output_data TEXT, -- JSON string
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (prompt_version_id) REFERENCES prompt_versions (id) ON DELETE CASCADE
                )
                """
            )
            await cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS evaluation_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ai_output_id INTEGER NOT NULL,
                    metric_scores TEXT, -- JSON dictionary
                    target_metrics_snapshot TEXT, -- JSON dictionary of the targets for this run
                    qualitative_feedback TEXT,
                    user_rating INTEGER,
                    overall_score REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (ai_output_id) REFERENCES ai_outputs (id) ON DELETE CASCADE
                )
                """
            )
            await self._conn.commit()

    async def _seed_initial_metaprompt(self):
        """Seeds the database with the initial 'Architect' meta-prompt if it doesn't exist."""
        # We use the name 'architect_v3' to ensure this new prompt is picked up,
        # and we set all other architect prompts to inactive.
        prompt_name = 'architect_v3'
        
        async with self._conn.cursor() as cursor:
            # Check if this specific version already exists
            await cursor.execute("SELECT id FROM meta_prompts WHERE name = ?", (prompt_name,))
            exists = await cursor.fetchone()
            
            if not exists:
                print(f"Seeding '{prompt_name}' meta-prompt into the database.")
                # Deactivate all other prompts that look like 'architect' prompts
                await cursor.execute("UPDATE meta_prompts SET is_active = 0 WHERE name LIKE 'architect%'")

                architect_prompt = MetaPrompt(
                    name=prompt_name,
                    template=_INITIAL_ARCHITECT_META_PROMPT,
                    is_active=True 
                )
                
                # Directly insert the new prompt using an INSERT statement
                insert_sql = "INSERT INTO meta_prompts (name, template, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?)"
                now = datetime.now(timezone.utc).isoformat()
                await cursor.execute(insert_sql, (
                    architect_prompt.name, 
                    architect_prompt.template, 
                    architect_prompt.is_active, 
                    now, 
                    now
                ))
                await self._conn.commit()
                print(f"Successfully seeded and activated '{prompt_name}'.")

    def _serialize_timestamps(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Converts datetime objects to ISO 8601 strings."""
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

    def _deserialize_timestamps(self, data: Dict[str, Any], model_cls: Type[T]) -> Dict[str, Any]:
        """Converts ISO 8601 strings back to datetime objects for datetime fields."""
        for field_name, field_type in model_cls.model_fields.items():
            if field_type.annotation == datetime and field_name in data and isinstance(data[field_name], str):
                try:
                    data[field_name] = datetime.fromisoformat(data[field_name])
                except ValueError:
                     # Handle cases where the string might not be a valid ISO format (e.g. old data)
                    print(f"Warning: Could not parse datetime string '{data[field_name]}' for field {field_name}")
        return data

    def _handle_json_serialization(self, data: Dict[str, Any], model_cls: Type[T]):
        """Serializes fields that should be stored as JSON strings."""
        # This is a bit of a hack. A better way would be to have a schema registry
        # that knows which fields are JSON.
        json_fields = {
            'AIOutput': ['raw_output_data'],
            'EvaluationResult': ['metric_scores', 'target_metrics_snapshot'],
            'TargetAIProfile': ['capabilities'] # Assuming 'capabilities' from schema is the field name
        }
        model_name = model_cls.__name__
        if model_name in json_fields:
            for field_name in json_fields[model_name]:
                if field_name in data and data[field_name] is not None:
                    data[field_name] = json.dumps(data[field_name])
        return data

    def _handle_json_deserialization(self, data: Dict[str, Any], model_cls: Type[T]):
        """Deserializes fields stored as JSON strings."""
        json_fields = {
            'AIOutput': ['raw_output_data'],
            'EvaluationResult': ['metric_scores', 'target_metrics_snapshot'],
            'TargetAIProfile': ['capabilities']
        }
        
        model_name = model_cls.__name__
        if model_name in json_fields:
            for field_name in json_fields[model_name]:
                if field_name in data and isinstance(data[field_name], str):
                    try:
                        data[field_name] = json.loads(data[field_name])
                    except json.JSONDecodeError:
                        print(f"Warning: Could not JSON decode field '{field_name}' for {model_cls.__name__}.")
        return data

    def _serialize_for_db(self, record: BaseMPLAModel) -> Dict[str, Any]:
        """Prepares a model to be inserted into the database, handling JSON fields."""
        if isinstance(record, MetaPrompt):
            table_name = "meta_prompts"
            data_dict = {"name": record.name, "template": record.template, "is_active": record.is_active}
        elif isinstance(record, OriginalPrompt):
            table_name = "original_prompts"
            data_dict = {"text": record.text, "user_id": record.user_id}
        elif isinstance(record, PromptVersion):
            table_name = "prompt_versions"
            data_dict = {
                "original_prompt_id": record.original_prompt_id,
                "iteration_id": record.iteration_id,
                "version_number": record.version_number,
                "prompt_text": record.prompt_text,
                "enhancement_rationale": record.enhancement_rationale,
                "target_ai_profile_id": record.target_ai_profile_id
            }
        elif isinstance(record, TargetAIProfile):
            table_name = "target_ai_profiles"
            data_dict = {
                "name": record.name,
                "api_endpoint": record.api_endpoint,
                "capabilities_json": json.dumps(record.capabilities or {}),
            }
        elif isinstance(record, AIOutput):
            table_name = "ai_outputs"
            data_dict = {
                "prompt_version_id": record.prompt_version_id, 
                "raw_output_data": json.dumps(record.raw_output_data or {})
            }
        elif isinstance(record, EvaluationResult):
            table_name = "evaluation_results"
            data_dict = {
                "ai_output_id": record.ai_output_id,
                "metric_scores": json.dumps(record.metric_scores or {}),
                "target_metrics_snapshot": json.dumps(record.target_metrics_snapshot or {}),
                "qualitative_feedback": record.qualitative_feedback,
                "user_rating": record.user_rating,
                "overall_score": record.overall_score
            }
        elif isinstance(record, IterationLog):
            table_name = "iteration_logs"
            data_dict = {
                "original_prompt_id": record.original_prompt_id,
                "session_id": record.session_id,
                "iteration_number": record.iteration_number,
                "active_prompt_version_id": record.active_prompt_version_id,
                "ai_output_id": record.ai_output_id,
                "evaluation_result_id": record.evaluation_result_id,
                "status": record.status
            }
        else:
            raise ValueError(f"Unsupported model type: {type(record).__name__}")
        
        return table_name, data_dict

    async def add(self, record: T) -> T:
        """Adds a new record to the database and returns the complete record with its ID."""
        if not self._conn:
            raise ConnectionError("Database not connected")

        table_name, data_to_insert = self._serialize_for_db(record)
        
        # Add timestamps
        now = datetime.now(timezone.utc).isoformat()
        data_to_insert['created_at'] = now
        data_to_insert['updated_at'] = now

        columns = ', '.join(data_to_insert.keys())
        placeholders = ', '.join('?' for _ in data_to_insert)
        
        sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
        
        async with self._conn.cursor() as cursor:
            await cursor.execute(sql, tuple(data_to_insert.values()))
            await self._conn.commit()
            record_id = cursor.lastrowid
        
        # Return a new object with the ID and other db-defaults set.
        # This is simpler than trying to mutate the original record.
        return await self.get(type(record), record_id)

    async def get(self, model_cls: Type[T], record_id: int) -> Optional[T]:
        """Retrieves a single record by its ID."""
        if not self._conn: await self.connect()
        table_name = self._get_table_name(model_cls)
        sql = f"SELECT * FROM {table_name} WHERE id = ?"

        async with self._conn.execute(sql, (record_id,)) as cursor:
            row = await cursor.fetchone()

        if row:
            data = dict(row)
            data = self._handle_json_deserialization(data, model_cls)
            data = self._deserialize_timestamps(data, model_cls)
            try:
                return model_cls(**data)
            except Exception as e: # Catch Pydantic validation errors or other issues
                print(f"Error constructing model {model_cls.__name__} from DB data: {e}, Data: {data}")
                return None
        return None

    async def update(self, record_id: int, update_data: T) -> Optional[T]:
        """Updates a record in the database."""
        if not self._conn: await self.connect()
        model_cls = type(update_data)
        table_name = self._get_table_name(model_cls)

        update_data.updated_at = datetime.now(timezone.utc)
        
        data_to_update = update_data.model_dump(exclude_none=True, exclude={'id', 'created_at'})
        if not data_to_update: # Only updated_at might change
            data_to_update['updated_at'] = update_data.updated_at
        
        data_to_update = self._handle_json_serialization(data_to_update, model_cls)
        data_to_update = self._serialize_timestamps(data_to_update)

        if not data_to_update:
             # If only id/created_at were in model, and updated_at is only change
            if 'updated_at' in data_to_update and len(data_to_update) == 1:
                 pass # Allow update of only updated_at
            else:
                return await self.get(model_cls, record_id)

        set_clause = ", ".join([f"{key} = ?" for key in data_to_update.keys()])
        sql = f"UPDATE {table_name} SET {set_clause} WHERE id = ?"
        values = list(data_to_update.values()) + [record_id]

        try:
            async with self._conn.cursor() as cursor:
                await cursor.execute(sql, values)
                await self._conn.commit()
            if cursor.rowcount > 0:
                return await self.get(model_cls, record_id)
            return None # Record with ID not found
        except aiosqlite.Error as e:
            print(f"SQLite error during update to {table_name} (ID: {record_id}): {e}")
            raise

    async def _execute_query_and_fetch_all(self, model_cls: Type[T], sql: str, params: tuple = ()) -> List[T]:
        """A generic method to execute a SELECT query and return a list of model instances."""
        if not self._conn: await self.connect()
        async with self._conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
        
        # Concurrently process all rows
        return await asyncio.gather(*(self._db_row_to_model(row, model_cls) for row in rows))

    async def get_prompt_versions_for_original(self, original_prompt_id: int) -> List[PromptVersion]:
        """Retrieves all prompt versions associated with a specific original prompt."""
        table_name = self._get_table_name(PromptVersion)
        sql = f"SELECT * FROM {table_name} WHERE original_prompt_id = ? ORDER BY version_number ASC"
        return await self._execute_query_and_fetch_all(PromptVersion, sql, (original_prompt_id,))

    async def get_evaluations_for_prompt_version(self, prompt_version_id: int) -> List[EvaluationResult]:
        """Retrieves all evaluations for a specific prompt version."""
        ai_outputs_table = self._get_table_name(AIOutput)
        eval_results_table = self._get_table_name(EvaluationResult)
        sql = f"""
            SELECT er.* FROM {eval_results_table} er
            JOIN {ai_outputs_table} ao ON er.ai_output_id = ao.id
            WHERE ao.prompt_version_id = ?
        """
        return await self._execute_query_and_fetch_all(EvaluationResult, sql, (prompt_version_id,))

    async def log_iteration(self, iteration_log: IterationLog) -> IterationLog:
        """Logs a new iteration and returns the logged iteration."""
        return await self.add(iteration_log)

    async def get_iteration_log(self, iteration_id: int) -> Optional[IterationLog]:
        """Retrieves a specific iteration log by its ID."""
        return await self.get(IterationLog, iteration_id)

    async def get_iterations_for_session(self, session_id: str) -> List[IterationLog]:
        """Retrieves all iteration logs for a given session ID."""
        table_name = self._get_table_name(IterationLog)
        sql = f"SELECT * FROM {table_name} WHERE session_id = ? ORDER BY iteration_number ASC"
        return await self._execute_query_and_fetch_all(IterationLog, sql, (session_id,))

    async def get_active_meta_prompt(self, name_like: str = "architect") -> Optional[MetaPrompt]:
        """
        Retrieves the currently active meta-prompt from the database.
        It prioritizes prompts with names matching the 'name_like' parameter.
        """
        table_name = self._get_table_name(MetaPrompt)
        # Prioritize finding the active prompt with the specified name pattern
        sql = f"SELECT * FROM {table_name} WHERE is_active = 1 AND name LIKE ? ORDER BY id DESC LIMIT 1"
        
        async with self._conn.execute(sql, (f'%{name_like}%',)) as cursor:
            row = await cursor.fetchone()
        
        if row:
            return await self._db_row_to_model(row, MetaPrompt)
        
        # Fallback: if no named active prompt is found, get the most recently activated one.
        sql_fallback = f"SELECT * FROM {table_name} WHERE is_active = 1 ORDER BY id DESC LIMIT 1"
        async with self._conn.execute(sql_fallback) as cursor:
            row_fallback = await cursor.fetchone()
            
        return await self._db_row_to_model(row_fallback, MetaPrompt) if row_fallback else None

    async def get_all(self, model_cls: Type[T]) -> List[T]:
        """Retrieves all records from a table."""
        table_name = self._get_table_name(model_cls)
        sql = f"SELECT * FROM {table_name}"
        return await self._execute_query_and_fetch_all(model_cls, sql)

    async def _db_row_to_model(self, row: aiosqlite.Row, model_cls: Type[T]) -> T:
        """Converts a row from the database into a Pydantic model instance."""
        data = dict(row)
        # Handle fields that are stored as JSON strings
        data = self._handle_json_deserialization(data, model_cls)
        return model_cls(**data)

    def _get_model_from_table(self, table_name: str) -> Optional[Type[BaseMPLAModel]]:
        """Maps a table name back to its corresponding Pydantic model class."""
        schema_map = {
            "meta_prompts": MetaPrompt,
            "original_prompts": OriginalPrompt,
            "prompt_versions": PromptVersion,
            "target_ai_profiles": TargetAIProfile,
            "ai_outputs": AIOutput,
            "evaluation_results": EvaluationResult,
            "iteration_logs": IterationLog,
        }
        return schema_map.get(table_name)
    
    # --- The methods below are potentially deprecated or need refactoring ---
    
    async def save_prompt_version(self, prompt_version: PromptVersion) -> PromptVersion:
        """Saves a new prompt version to the database."""
        # Deprecated in favor of add()
        return await self.add(prompt_version)
    
    async def get_latest_prompt_version(self, original_prompt_id: int) -> Optional[PromptVersion]:
        """Retrieves the latest prompt version for a given original prompt ID."""
        table_name = self._get_table_name(PromptVersion)
        sql = f"SELECT * FROM {table_name} WHERE original_prompt_id = ? ORDER BY version_number DESC LIMIT 1"
        async with self._conn.execute(sql, (original_prompt_id,)) as cursor:
            row = await cursor.fetchone()
        return await self._db_row_to_model(row, PromptVersion) if row else None

    async def save_evaluation_result(self, result: EvaluationResult) -> EvaluationResult:
        """Saves an evaluation result to the database."""
        # Deprecated in favor of add()
        return await self.add(result)
    
    async def save_ai_output(self, output: AIOutput) -> AIOutput:
        """Saves an AI output to the database."""
        # Deprecated in favor of add()
        return await self.add(output)

# Example usage for manual testing:
# async def main():
#     kb = SQLiteKnowledgeBase(db_path='mpla_v2.db')
#     await kb.connect()
#
#     # Create an OriginalPrompt
#     op = OriginalPrompt(text="What is the meaning of life?")
#     added_op = await kb.add(op)
#     print(f"Added OriginalPrompt: {added_op}")
#
#     # Create a TargetAIProfile
#     tap = TargetAIProfile(name="test_profile", capabilities={"model": "test_model"})
#     added_tap = await kb.add(tap)
#     print(f"Added TargetAIProfile: {added_tap}")
#
#     # Create an IterationLog
#     il = IterationLog(
#         original_prompt_id=added_op.id,
#         session_id="session123",
#         iteration_number=1,
#         status="testing"
#     )
#     added_il = await kb.add(il)
#     print(f"Added IterationLog: {added_il}")
#
#     # Create a PromptVersion
#     pv = PromptVersion(
#             original_prompt_id=added_op.id,
#             iteration_id=added_il.id,
#             version_number=1,
#             prompt_text="Explain relativity like I'm five.",
#             enhancement_rationale="Simplified language for younger audience.",
#             target_ai_profile_id=added_tap.id
#     )
#     added_pv = await kb.add(pv)
#     print(f"Added PromptVersion: {added_pv}")
#
#
#     # Get all prompt versions for the original prompt
#     pvs = await kb.get_prompt_versions_for_original(added_op.id)
#     print(f"Got PromptVersions: {pvs}")
#
#     await kb.disconnect()
#
# if __name__ == '__main__':
#     import asyncio
#     asyncio.run(main()) 