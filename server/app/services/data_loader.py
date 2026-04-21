"""
Data loader for special education curriculum standards.
Loads JSON files containing achievement standards and converts them into documents
suitable for vector embedding and RAG retrieval.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AchievementStandard:
    """Represents a single achievement standard document."""
    grade: str
    subject: str
    disability_type: str
    achievement_standard: str
    learning_objectives: List[str]
    scaffolding_levels: Dict[str, str]
    activities: List[str]

    def to_document(self) -> Dict[str, Any]:
        """Convert to a document format suitable for vector embedding."""
        content = f"""
학년: {self.grade}
과목: {self.subject}
장애 유형: {self.disability_type}

성취기준: {self.achievement_standard}

학습 목표:
{chr(10).join(f"- {obj}" for obj in self.learning_objectives)}

스캐폴딩 수준:
높음: {self.scaffolding_levels.get('high', 'N/A')}
중간: {self.scaffolding_levels.get('medium', 'N/A')}
낮음: {self.scaffolding_levels.get('low', 'N/A')}

활동:
{chr(10).join(f"- {activity}" for activity in self.activities)}
        """.strip()

        metadata = {
            "grade": self.grade,
            "subject": self.subject,
            "disability_type": self.disability_type,
            "source": "special_education_standards",
            "content_type": "achievement_standard"
        }

        return {
            "content": content,
            "metadata": metadata,
            "id": f"{self.grade}_{self.subject}_{self.disability_type}_{hash(self.achievement_standard) % 10000}"
        }


class DataLoader:
    """Loads and processes special education curriculum data from JSON files."""

    def __init__(self, data_dir: str = "server/data"):
        self.data_dir = Path(data_dir)
        self.logger = logging.getLogger(__name__)

    def load_standards_from_json(self, filename: str) -> List[AchievementStandard]:
        """
        Load achievement standards from a JSON file.

        Args:
            filename: Name of the JSON file in the data directory

        Returns:
            List of AchievementStandard objects
        """
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            standards = []
            for item in data:
                standard = AchievementStandard(
                    grade=item.get('grade', ''),
                    subject=item.get('subject', ''),
                    disability_type=item.get('disability_type', ''),
                    achievement_standard=item.get('achievement_standard', ''),
                    learning_objectives=item.get('learning_objectives', []),
                    scaffolding_levels=item.get('scaffolding_levels', {}),
                    activities=item.get('activities', [])
                )
                standards.append(standard)

            self.logger.info(f"Loaded {len(standards)} achievement standards from {filename}")
            return standards

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {filename}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading {filename}: {e}")
            raise

    def load_all_standards(self) -> List[AchievementStandard]:
        """
        Load all achievement standards from available JSON files.

        Currently supports:
        - special_education_standards.json
        """
        all_standards = []

        # Load special education standards
        try:
            standards = self.load_standards_from_json("special_education_standards.json")
            all_standards.extend(standards)
        except FileNotFoundError:
            self.logger.warning("special_education_standards.json not found")
        except Exception as e:
            self.logger.error(f"Error loading special education standards: {e}")

        # Future: Add more JSON files as needed
        # try:
        #     standards = self.load_standards_from_json("standards_pool.json")
        #     all_standards.extend(standards)
        # except FileNotFoundError:
        #     self.logger.warning("standards_pool.json not found")

        return all_standards

    def get_documents_for_embedding(self) -> List[Dict[str, Any]]:
        """
        Get all standards as documents ready for vector embedding.

        Returns:
            List of document dictionaries with content, metadata, and IDs
        """
        standards = self.load_all_standards()
        documents = []

        for standard in standards:
            doc = standard.to_document()
            documents.append(doc)

        self.logger.info(f"Prepared {len(documents)} documents for embedding")
        return documents

    def get_standards_by_criteria(
        self,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        disability_type: Optional[str] = None
    ) -> List[AchievementStandard]:
        """
        Filter standards by specific criteria.

        Args:
            grade: Filter by grade (e.g., "초등학교 1학년")
            subject: Filter by subject (e.g., "국어", "수학")
            disability_type: Filter by disability type (e.g., "지적장애", "학습장애")

        Returns:
            Filtered list of AchievementStandard objects
        """
        all_standards = self.load_all_standards()
        filtered = all_standards

        if grade:
            filtered = [s for s in filtered if s.grade == grade]
        if subject:
            filtered = [s for s in filtered if s.subject == subject]
        if disability_type:
            filtered = [s for s in filtered if s.disability_type == disability_type]

        return filtered