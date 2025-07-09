from abc import ABC, abstractmethod
from typing import List, Optional, TypeVar, Type, Generic

from .schemas import BaseMPLAModel, OriginalPrompt, PromptVersion, EvaluationResult, IterationLog, TargetAIProfile, AIOutput

# Generic TypeVar for CRUD operations
T = TypeVar('T', bound=BaseMPLAModel)

class KnowledgeBase(ABC):
    """Abstract Base Class for the Knowledge Base / Memory component.
    
    Defines the interface for storing and retrieving all data related to
    prompt refinement cycles.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Close connection to the database."""
        pass

    @abstractmethod
    async def add(self, record: T) -> T:
        """Adds a new record to the database and returns the persisted record (e.g., with ID).

        Args:
            record (T): The Pydantic model instance to add.

        Returns:
            T: The persisted Pydantic model instance, potentially updated (e.g., with an ID).
        """
        pass

    @abstractmethod
    async def get(self, model: Type[T], record_id: int) -> Optional[T]:
        """Retrieves a record by its ID.

        Args:
            model (Type[T]): The Pydantic model class of the record to retrieve.
            record_id (int): The ID of the record.

        Returns:
            Optional[T]: The retrieved record or None if not found.
        """
        pass

    @abstractmethod
    async def update(self, record_id: int, update_data: T) -> Optional[T]:
        """Updates an existing record.

        Args:
            record_id (int): The ID of the record to update.
            update_data (T): A Pydantic model instance containing the fields to update.
                             The `id` field in update_data is ignored.

        Returns:
            Optional[T]: The updated record or None if not found.
        """
        pass

    # Specific methods for MPLA entities (examples)

    @abstractmethod
    async def get_prompt_versions_for_original(self, original_prompt_id: int) -> List[PromptVersion]:
        """Retrieves all prompt versions associated with an original prompt."""
        pass

    @abstractmethod
    async def get_evaluations_for_prompt_version(self, prompt_version_id: int) -> List[EvaluationResult]:
        """Retrieves all evaluation results for a specific prompt version."""
        pass

    @abstractmethod
    async def log_iteration(self, iteration_log: IterationLog) -> IterationLog:
        """Logs a new iteration cycle."""
        pass

    @abstractmethod
    async def get_iteration_log(self, iteration_id: int) -> Optional[IterationLog]:
        """Retrieves a specific iteration log."""
        pass

    @abstractmethod
    async def get_iterations_for_session(self, session_id: str) -> List[IterationLog]:
        """Retrieves all iterations for a given session ID."""
        pass

    # Add more specific query methods as needed, e.g., for LearnedStrategy, RefinementLog etc.

# Example of a concrete implementation (e.g., for SQLite or PostgreSQL) would inherit from this.
# class SQLiteKnowledgeBase(KnowledgeBase):
#     def __init__(self, db_path: str):
#         self.db_path = db_path
#         # ... initialization ...

#     async def connect(self) -> None:
#         # ... connect to SQLite ...
#         print(f"Connected to SQLite DB at {self.db_path}")
#         pass

#     async def disconnect(self) -> None:
#         # ... disconnect from SQLite ...
#         print("Disconnected from SQLite DB")
#         pass

#     async def add(self, record: T) -> T:
#         # ... implementation ...
#         print(f"Adding record: {record}")
#         # Simulate ID assignment
#         if not record.id:
#             record.id = random.randint(1, 10000)
#         record.created_at = datetime.utcnow()
#         record.updated_at = datetime.utcnow()
#         # In a real scenario, this would interact with the DB
#         return record
    
#     async def get(self, model: Type[T], record_id: int) -> Optional[T]:
#         print(f"Getting record type {model.__name__} with ID: {record_id}")
#         # Simulate DB fetch
#         return None 

#     async def update(self, record_id: int, update_data: T) -> Optional[T]:
#         print(f"Updating record ID {record_id} with data: {update_data}")
#         # Simulate DB update
#         update_data.id = record_id # Ensure ID is set correctly
#         update_data.updated_at = datetime.utcnow()
#         return update_data

#     async def get_prompt_versions_for_original(self, original_prompt_id: int) -> List[PromptVersion]:
#         return []

#     async def get_evaluations_for_prompt_version(self, prompt_version_id: int) -> List[EvaluationResult]:
#         return []

#     async def log_iteration(self, iteration_log: IterationLog) -> IterationLog:
#         return await self.add(iteration_log)
    
#     async def get_iteration_log(self, iteration_id: int) -> Optional[IterationLog]:
#         return None
    
#     async def get_iterations_for_session(self, session_id: str) -> List[IterationLog]:
#         return []

# # For testing
# import random
# from datetime import datetime 