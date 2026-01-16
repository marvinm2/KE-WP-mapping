"""
Service Container for Dependency Injection
Provides centralized management of application services and dependencies
"""
import logging

from authlib.integrations.flask_client import OAuth

from models import CacheModel, Database, MappingModel, ProposalModel
from monitoring import MetricsCollector
from pathway_suggestions import PathwaySuggestionService
from rate_limiter import RateLimiter
from config_loader import ConfigLoader
from embedding_service import BiologicalEmbeddingService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing application services

    This container follows the singleton pattern for database connections
    and provides factory methods for creating service instances.
    """

    def __init__(self, config):
        self.config = config
        self._database = None
        self._mapping_model = None
        self._proposal_model = None
        self._cache_model = None
        self._metrics_collector = None
        self._rate_limiter = None
        self._pathway_suggestion_service = None
        self._oauth = None
        self._github_client = None
        self._scoring_config = None
        self._embedding_service = None

        logger.info("Service container initialized")

    @property
    def database(self) -> Database:
        """Get or create database instance (singleton)"""
        if self._database is None:
            self._database = Database(self.config.DATABASE_PATH)
            logger.info(f"Database instance created: {self.config.DATABASE_PATH}")
        return self._database

    @property
    def mapping_model(self) -> MappingModel:
        """Get or create mapping model instance"""
        if self._mapping_model is None:
            self._mapping_model = MappingModel(self.database)
            logger.debug("MappingModel instance created")
        return self._mapping_model

    @property
    def proposal_model(self) -> ProposalModel:
        """Get or create proposal model instance"""
        if self._proposal_model is None:
            self._proposal_model = ProposalModel(self.database)
            logger.debug("ProposalModel instance created")
        return self._proposal_model

    @property
    def cache_model(self) -> CacheModel:
        """Get or create cache model instance"""
        if self._cache_model is None:
            self._cache_model = CacheModel(self.database)
            logger.debug("CacheModel instance created")
        return self._cache_model

    @property
    def metrics_collector(self) -> MetricsCollector:
        """Get or create metrics collector instance"""
        if self._metrics_collector is None:
            self._metrics_collector = MetricsCollector(self.config.DATABASE_PATH)
            logger.debug("MetricsCollector instance created")
        return self._metrics_collector

    @property
    def rate_limiter(self) -> RateLimiter:
        """Get or create rate limiter instance"""
        if self._rate_limiter is None:
            self._rate_limiter = RateLimiter(self.config.DATABASE_PATH)
            logger.debug("RateLimiter instance created")
        return self._rate_limiter

    @property
    def scoring_config(self):
        """Get or load scoring configuration"""
        if self._scoring_config is None:
            try:
                self._scoring_config = ConfigLoader.load_config()
                logger.info("Scoring configuration loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load scoring config: {e}")
                self._scoring_config = ConfigLoader.get_default_config()
                logger.info("Using default scoring configuration")
        return self._scoring_config

    @property
    def pathway_suggestion_service(self) -> PathwaySuggestionService:
        """Get or create pathway suggestion service instance"""
        if self._pathway_suggestion_service is None:
            scoring_config = self.scoring_config
            self._pathway_suggestion_service = PathwaySuggestionService(
                self.cache_model,
                config=scoring_config,
                embedding_service=self.embedding_service
            )
            logger.debug("PathwaySuggestionService instance created with config")
        return self._pathway_suggestion_service

    @property
    def embedding_service(self) -> BiologicalEmbeddingService:
        """Get or create embedding service instance"""
        if self._embedding_service is None:
            try:
                # Check if embeddings are enabled
                embedding_config = getattr(
                    self.scoring_config.pathway_suggestion,
                    'embedding_based_matching',
                    None
                )

                enabled = getattr(embedding_config, 'enabled', False) if embedding_config else False

                if enabled:
                    model_name = getattr(
                        embedding_config,
                        'model',
                        'dmis-lab/biobert-base-cased-v1.2'
                    )
                    precomputed_path = getattr(
                        embedding_config,
                        'precomputed_embeddings',
                        'pathway_embeddings.npy'
                    )
                    precomputed_ke_path = getattr(
                        embedding_config,
                        'precomputed_ke_embeddings',
                        'ke_embeddings.npy'
                    )

                    self._embedding_service = BiologicalEmbeddingService(
                        model_name=model_name,
                        use_gpu=True,
                        precomputed_embeddings_path=precomputed_path,
                        precomputed_ke_embeddings_path=precomputed_ke_path
                    )
                    logger.info("Embedding service initialized")
                else:
                    logger.info("Embedding service disabled by config")
                    self._embedding_service = None

            except Exception as e:
                logger.error(f"Failed to initialize embedding service: {e}")
                self._embedding_service = None

        return self._embedding_service

    def init_oauth(self, app) -> OAuth:
        """Initialize OAuth with the Flask app"""
        if self._oauth is None:
            self._oauth = OAuth(app)
            self._github_client = self._oauth.register(
                name="github",
                client_id=self.config.GITHUB_CLIENT_ID,
                client_secret=self.config.GITHUB_CLIENT_SECRET,
                access_token_url="https://github.com/login/oauth/access_token",
                authorize_url="https://github.com/login/oauth/authorize",
                api_base_url="https://api.github.com/",
                client_kwargs={"scope": "user:email"},
            )
            logger.info("OAuth initialized with GitHub")
        return self._oauth

    @property
    def github_client(self):
        """Get GitHub OAuth client"""
        if self._github_client is None:
            raise RuntimeError("OAuth not initialized. Call init_oauth() first.")
        return self._github_client

    def cleanup(self):
        """Cleanup resources on shutdown"""
        if self._metrics_collector:
            # Cleanup any background threads in metrics collector
            logger.info("Cleaning up metrics collector")

        if self._database:
            # Database connections are automatically closed in models
            logger.info("Database cleanup completed")

        logger.info("Service container cleanup completed")

    def get_health_status(self) -> dict:
        """Get health status of all services"""
        status = {
            "database": False,
            "oauth": False,
            "services": {
                "mapping_model": self._mapping_model is not None,
                "proposal_model": self._proposal_model is not None,
                "cache_model": self._cache_model is not None,
                "metrics_collector": self._metrics_collector is not None,
                "rate_limiter": self._rate_limiter is not None,
                "pathway_suggestion_service": self._pathway_suggestion_service is not None,
            },
        }

        # Test database connection
        try:
            conn = self.database.get_connection()
            conn.execute("SELECT 1")
            conn.close()
            status["database"] = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        # Test OAuth configuration
        try:
            status["oauth"] = bool(
                self.config.GITHUB_CLIENT_ID and self.config.GITHUB_CLIENT_SECRET
            )
        except Exception as e:
            logger.error(f"OAuth health check failed: {e}")

        return status
