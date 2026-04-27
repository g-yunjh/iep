"""Data loader for special education curriculum and career data.
Loads JSON files containing achievement standards and career data,
converts them into documents suitable for vector embedding and RAG retrieval.
"""

import json
import logging
import hashlib
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AchievementStandard:
    """Represents a single achievement standard document."""
    standard_id: str
    grade: str
    subject: str
    source: str
    domain: str
    disability_type: str
    achievement_standard: str
    learning_objectives: List[str]
    scaffolding_levels: Dict[str, str]
    activities: List[str]

    @staticmethod
    def _stringify_item(item: Any) -> str:
        """Normalize mixed JSON items (str/dict/etc.) into readable text."""
        if isinstance(item, str):
            return item
        if isinstance(item, dict):
            for key in ("indicator", "text", "description", "label", "name"):
                value = item.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            return " ".join(str(v).strip() for v in item.values() if str(v).strip())
        return str(item).strip()

    def to_document(self) -> Dict[str, Any]:
        """Convert to a document format suitable for vector embedding."""
        learning_objective_lines = [
            f"- {self._stringify_item(obj)}"
            for obj in self.learning_objectives
            if self._stringify_item(obj)
        ]
        activity_lines = [
            f"- {self._stringify_item(activity)}"
            for activity in self.activities
            if self._stringify_item(activity)
        ]

        general_scaffolding = self.scaffolding_levels.get("general", [])
        if isinstance(general_scaffolding, list):
            general_scaffolding_text = "; ".join(
                self._stringify_item(item) for item in general_scaffolding if self._stringify_item(item)
            ) or "N/A"
        else:
            general_scaffolding_text = self._stringify_item(general_scaffolding) or "N/A"

        disability_specific = self.scaffolding_levels.get("disability_specific", {})
        if isinstance(disability_specific, dict):
            disability_scaffolding_text = "; ".join(
                f"{k}: {self._stringify_item(v)}"
                for k, v in disability_specific.items()
                if self._stringify_item(v)
            ) or "N/A"
        else:
            disability_scaffolding_text = self._stringify_item(disability_specific) or "N/A"

        content = f"""
학년: {self.grade}
과목: {self.subject}
장애 유형: {self.disability_type}
성취기준 ID: {self.standard_id}

성취기준: {self.achievement_standard}

학습 목표:
{chr(10).join(learning_objective_lines)}

스캐폴딩 수준:
일반: {general_scaffolding_text}
장애특성: {disability_scaffolding_text}

활동:
{chr(10).join(activity_lines)}
        """.strip()

        metadata = {
            "achievement_standard_id": self.standard_id,
            "grade": self.grade,
            "subject": self.subject,
            "domain": self.domain,
            "disability_type": self.disability_type,
            "source": self.source,
            "content_type": "achievement_standard"
        }

        fallback_id_source = f"{self.subject}|{self.grade}|{self.achievement_standard}"
        fallback_id = hashlib.md5(fallback_id_source.encode("utf-8")).hexdigest()[:12]
        document_id = self.standard_id or fallback_id

        return {
            "content": content,
            "metadata": metadata,
            "id": document_id
        }


@dataclass
class CareerData:
    """Represents a single career data document."""
    job_id: str
    job_title: str
    category: str
    search_keywords: List[str]
    job_logic: str
    competency_indicators: Dict[str, Any]
    roadmap_bank: Dict[str, Any]
    outlook_scaffolding: str

    def to_document(self) -> Dict[str, Any]:
        """Convert to a document format suitable for vector embedding."""
        cognitive = self.competency_indicators.get("cognitive_skills", [])
        soft = self.competency_indicators.get("soft_skills", [])
        
        content = f"""
직업: {self.job_title}
분류: {self.category}
직업 설명: {self.job_logic}

핵심 역량:
{chr(10).join(f"- {skill}" for skill in cognitive + soft)}

자격증: {', '.join(self.roadmap_bank.get('certifications', []))}
진로 전망: {self.outlook_scaffolding}
        """.strip()

        metadata = {
            "job_id": self.job_id,
            "job_title": self.job_title,
            "category": self.category,
            "source": "career_net",
            "content_type": "career"
        }

        return {
            "content": content,
            "metadata": metadata,
            "id": self.job_id
        }


class DataLoader:
    """Loads and processes special education curriculum and career data from JSON files."""

    def __init__(self, data_dir: Optional[str] = None):
        # Resolve paths from repository root so startup directory does not matter.
        self.project_root = Path(__file__).resolve().parents[3]
        self.server_root = self.project_root / "server"
        default_data_dir = self.server_root / "data"
        self.data_dir = self._resolve_data_dir(data_dir, default_data_dir)
        self.logger = logging.getLogger(__name__)
        self._validate_data_dir_exists()

    def _resolve_data_dir(self, data_dir: Optional[str], default_data_dir: Path) -> Path:
        """Resolve data directory as absolute path from project root."""
        if not data_dir:
            return default_data_dir.resolve()

        user_path = Path(data_dir).expanduser()
        if user_path.is_absolute():
            return user_path.resolve()
        return (self.project_root / user_path).resolve()

    def _validate_data_dir_exists(self) -> None:
        """Validate data directory and log all searched locations when missing."""
        if self.data_dir.exists():
            self.logger.info("Data directory resolved: %s", self.data_dir)
            return

        searched_paths = [
            self.data_dir,
            self.server_root / "data",
            self.project_root / "data",
        ]
        searched_message = ", ".join(str(path.resolve()) for path in searched_paths)
        self.logger.error("Data directory not found. Checked paths: %s", searched_message)

    def load_standards_from_json(self, filename: str) -> List[AchievementStandard]:
        """Load achievement standards from a JSON file."""
        file_path = self.data_dir / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            standards = []
            for item in data:
                standard = AchievementStandard(
                    standard_id=item.get('id', ''),
                    grade=item.get('grade', ''),
                    subject=item.get('subject', ''),
                    source=filename,
                    domain="legacy",
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

    def load_career_from_json(self, filename: str) -> List[CareerData]:
        """Load career data from a JSON file."""
        file_path = self.data_dir / "careers" / filename

        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            careers = []
            for item in data:
                career = CareerData(
                    job_id=item.get('job_id', ''),
                    job_title=item.get('job_title', ''),
                    category=item.get('category', ''),
                    search_keywords=item.get('search_keywords', []),
                    job_logic=item.get('job_logic', ''),
                    competency_indicators=item.get('competency_indicators', {}),
                    roadmap_bank=item.get('roadmap_bank', {}),
                    outlook_scaffolding=item.get('outlook_scaffolding', '')
                )
                careers.append(career)

            self.logger.info(f"Loaded {len(careers)} career data from {filename}")
            return careers

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {filename}: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Error loading {filename}: {e}")
            raise

    def load_curriculum_from_directory(self) -> List[AchievementStandard]:
        """Load all curriculum data from the curriculum directory."""
        all_standards = []
        curriculum_dir = self.data_dir / "curriculum"

        if not curriculum_dir.exists():
            self.logger.warning("Curriculum directory not found")
            return all_standards

        # Walk through all subdirectories
        for subject_dir in curriculum_dir.iterdir():
            if subject_dir.is_dir():
                subject = subject_dir.name
                # Load all JSON files in the subject directory
                for json_file in subject_dir.glob("*.json"):
                    try:
                        standards = self._load_curriculum_file(json_file, subject)
                        all_standards.extend(standards)
                    except Exception as e:
                        self.logger.error(f"Error loading {json_file}: {e}")

        self.logger.info(f"Loaded {len(all_standards)} curriculum standards total")
        return all_standards

    def _load_curriculum_file(self, file_path: Path, subject: str) -> List[AchievementStandard]:
        """Load a single curriculum JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        standards = []
        source_name = f"curriculum/{subject}/{file_path.name}"
        domain = file_path.stem
        for item in data:
            # Parse grade from id prefix like "9국어01-04", fallback to explicit grade.
            standard_id = str(item.get('id', '')).strip()
            grade_match = re.match(r"^(\d+)", standard_id)
            parsed_grade = grade_match.group(1) if grade_match else ""
            grade = str(item.get('grade') or parsed_grade or "")
            disability_specific = item.get('scaffolding_bank', {}).get('disability_specific', {})
            disability_type = ", ".join(disability_specific.keys()) if isinstance(disability_specific, dict) else ""
            
            standard = AchievementStandard(
                standard_id=standard_id,
                grade=grade,
                subject=subject,
                source=source_name,
                domain=domain,
                disability_type=disability_type,
                achievement_standard=item.get('goal', ''),
                learning_objectives=item.get('search_keywords', []),
                scaffolding_levels=item.get('scaffolding_bank', {}),
                activities=item.get('diagnostic_criteria', [])
            )
            standards.append(standard)

        return standards

    def load_all_standards(self) -> List[AchievementStandard]:
        """Load all achievement standards from available JSON files."""
        all_standards = []

        # Load from curriculum directory
        curriculum_standards = self.load_curriculum_from_directory()
        all_standards.extend(curriculum_standards)

        # Load special education standards (legacy)
        try:
            standards = self.load_standards_from_json("special_education_standards.json")
            all_standards.extend(standards)
        except FileNotFoundError:
            self.logger.warning("special_education_standards.json not found")
        except Exception as e:
            self.logger.error(f"Error loading special education standards: {e}")

        return all_standards

    def load_all_careers(self) -> List[CareerData]:
        """Load all career data from JSON files."""
        all_careers = []
        careers_dir = self.data_dir / "careers"

        if not careers_dir.exists():
            self.logger.warning("Careers directory not found")
            return all_careers

        # Load all job batch files
        for json_file in sorted(careers_dir.glob("jobs_batch_*.json")):
            try:
                careers = self.load_career_from_json(json_file.name)
                all_careers.extend(careers)
            except Exception as e:
                self.logger.error(f"Error loading {json_file}: {e}")

        self.logger.info(f"Loaded {len(all_careers)} career data total")
        return all_careers

    def get_documents_for_embedding(self, data_type: str = "all") -> List[Dict[str, Any]]:
        """
        Get documents ready for vector embedding.

        Args:
            data_type: Type of data to load ("curriculum", "career", or "all")

        Returns:
            List of document dictionaries with content, metadata, and IDs
        """
        documents = []

        if data_type in ("all", "curriculum"):
            standards = self.load_all_standards()
            for standard in standards:
                doc = standard.to_document()
                documents.append(doc)

        if data_type in ("all", "career"):
            careers = self.load_all_careers()
            for career in careers:
                doc = career.to_document()
                documents.append(doc)

        self.logger.info(f"Prepared {len(documents)} documents for embedding ({data_type})")
        return documents

    def get_standards_by_criteria(
        self,
        grade: Optional[str] = None,
        subject: Optional[str] = None,
        disability_type: Optional[str] = None
    ) -> List[AchievementStandard]:
        """Filter standards by specific criteria."""
        all_standards = self.load_all_standards()
        filtered = all_standards

        if grade:
            filtered = [s for s in filtered if s.grade == grade]
        if subject:
            filtered = [s for s in filtered if s.subject == subject]
        if disability_type:
            filtered = [s for s in filtered if s.disability_type == disability_type]

        return filtered