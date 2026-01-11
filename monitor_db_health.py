"""
Database Health Monitoring Module
Monitors database size, table statistics, and health metrics for beta testing
Created: 2026-01-11 06:31:21 UTC
"""

import sqlite3
import psycopg2
import mysql.connector
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('db_health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    """Supported database types"""
    SQLITE = "sqlite"
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


@dataclass
class DatabaseMetrics:
    """Data class for database health metrics"""
    db_type: str
    timestamp: str
    total_size_mb: float
    table_count: int
    connection_status: bool
    health_score: float
    warnings: List[str]
    table_stats: List[Dict]


class DatabaseHealthMonitor:
    """
    Monitor and track database health metrics including:
    - Database size
    - Table statistics
    - Connection health
    - Performance indicators
    """

    def __init__(self, db_config: Dict):
        """
        Initialize the database health monitor
        
        Args:
            db_config: Database configuration dictionary containing:
                - type: Database type (sqlite, postgresql, mysql)
                - path/host: Database location
                - Other connection parameters
        """
        self.db_config = db_config
        self.db_type = DatabaseType[db_config.get('type', 'SQLITE').upper()]
        self.connection = None
        self.health_history = []
        
    def connect(self) -> bool:
        """
        Establish database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            if self.db_type == DatabaseType.SQLITE:
                db_path = self.db_config.get('path', 'bot.db')
                self.connection = sqlite3.connect(db_path)
                self.connection.row_factory = sqlite3.Row
                logger.info(f"Connected to SQLite database: {db_path}")
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                self.connection = psycopg2.connect(
                    host=self.db_config.get('host'),
                    user=self.db_config.get('user'),
                    password=self.db_config.get('password'),
                    database=self.db_config.get('database'),
                    port=self.db_config.get('port', 5432)
                )
                logger.info(f"Connected to PostgreSQL database: {self.db_config.get('database')}")
                
            elif self.db_type == DatabaseType.MYSQL:
                self.connection = mysql.connector.connect(
                    host=self.db_config.get('host'),
                    user=self.db_config.get('user'),
                    password=self.db_config.get('password'),
                    database=self.db_config.get('database'),
                    port=self.db_config.get('port', 3306)
                )
                logger.info(f"Connected to MySQL database: {self.db_config.get('database')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Close database connection"""
        try:
            if self.connection:
                self.connection.close()
                logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {str(e)}")
    
    def get_database_size(self) -> float:
        """
        Get total database size in MB
        
        Returns:
            float: Database size in MB
        """
        try:
            if self.db_type == DatabaseType.SQLITE:
                db_path = self.db_config.get('path', 'bot.db')
                if os.path.exists(db_path):
                    size_bytes = os.path.getsize(db_path)
                    return size_bytes / (1024 * 1024)
                return 0.0
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT pg_database_size(current_database()) / 1024 / 1024 as size_mb;"
                )
                result = cursor.fetchone()
                cursor.close()
                return float(result[0]) if result else 0.0
                
            elif self.db_type == DatabaseType.MYSQL:
                cursor = self.connection.cursor()
                db_name = self.db_config.get('database')
                cursor.execute(
                    f"SELECT ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) "
                    f"FROM information_schema.tables WHERE table_schema = '{db_name}';"
                )
                result = cursor.fetchone()
                cursor.close()
                return float(result[0]) if result and result[0] else 0.0
                
        except Exception as e:
            logger.error(f"Error getting database size: {str(e)}")
            return 0.0
    
    def get_table_statistics(self) -> List[Dict]:
        """
        Get statistics for all tables
        
        Returns:
            List of dictionaries containing table statistics
        """
        stats = []
        
        try:
            if self.db_type == DatabaseType.SQLITE:
                cursor = self.connection.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = cursor.fetchall()
                
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
                    row_count = cursor.fetchone()[0]
                    
                    cursor.execute(f"PRAGMA table_info({table_name});")
                    columns = cursor.fetchall()
                    
                    stats.append({
                        'table_name': table_name,
                        'row_count': row_count,
                        'column_count': len(columns),
                        'size_estimate_mb': 0.0
                    })
                cursor.close()
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                cursor = self.connection.cursor()
                query = """
                    SELECT 
                        tablename,
                        schemaname
                    FROM pg_tables 
                    WHERE schemaname NOT IN ('pg_catalog', 'information_schema');
                """
                cursor.execute(query)
                tables = cursor.fetchall()
                
                for table_schema, table_name in tables:
                    # Row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_schema}.{table_name};")
                    row_count = cursor.fetchone()[0]
                    
                    # Table size
                    cursor.execute(
                        f"SELECT pg_total_relation_size('{table_schema}.{table_name}') / 1024 / 1024;"
                    )
                    size_mb = float(cursor.fetchone()[0])
                    
                    # Column count
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM information_schema.columns 
                        WHERE table_schema = '{table_schema}' AND table_name = '{table_name}';
                    """)
                    column_count = cursor.fetchone()[0]
                    
                    stats.append({
                        'table_name': table_name,
                        'row_count': row_count,
                        'column_count': column_count,
                        'size_estimate_mb': size_mb
                    })
                cursor.close()
                
            elif self.db_type == DatabaseType.MYSQL:
                cursor = self.connection.cursor()
                db_name = self.db_config.get('database')
                query = f"""
                    SELECT 
                        TABLE_NAME,
                        TABLE_ROWS,
                        ROUND((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024, 2)
                    FROM information_schema.TABLES 
                    WHERE TABLE_SCHEMA = '{db_name}';
                """
                cursor.execute(query)
                tables = cursor.fetchall()
                
                for table_name, row_count, size_mb in tables:
                    cursor.execute(
                        f"SELECT COUNT(*) FROM information_schema.COLUMNS "
                        f"WHERE TABLE_SCHEMA = '{db_name}' AND TABLE_NAME = '{table_name}';"
                    )
                    column_count = cursor.fetchone()[0]
                    
                    stats.append({
                        'table_name': table_name,
                        'row_count': row_count or 0,
                        'column_count': column_count,
                        'size_estimate_mb': size_mb or 0.0
                    })
                cursor.close()
                
        except Exception as e:
            logger.error(f"Error getting table statistics: {str(e)}")
        
        return stats
    
    def get_table_count(self) -> int:
        """
        Get total number of tables in database
        
        Returns:
            int: Number of tables
        """
        try:
            if self.db_type == DatabaseType.SQLITE:
                cursor = self.connection.cursor()
                cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
                count = cursor.fetchone()[0]
                cursor.close()
                return count
                
            elif self.db_type == DatabaseType.POSTGRESQL:
                cursor = self.connection.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM pg_tables "
                    "WHERE schemaname NOT IN ('pg_catalog', 'information_schema');"
                )
                count = cursor.fetchone()[0]
                cursor.close()
                return count
                
            elif self.db_type == DatabaseType.MYSQL:
                cursor = self.connection.cursor()
                db_name = self.db_config.get('database')
                cursor.execute(
                    f"SELECT COUNT(*) FROM information_schema.TABLES "
                    f"WHERE TABLE_SCHEMA = '{db_name}';"
                )
                count = cursor.fetchone()[0]
                cursor.close()
                return count
                
        except Exception as e:
            logger.error(f"Error getting table count: {str(e)}")
            return 0
    
    def check_health(self) -> DatabaseMetrics:
        """
        Perform comprehensive database health check
        
        Returns:
            DatabaseMetrics: Health metrics object
        """
        connection_status = self.connect()
        warnings = []
        health_score = 100.0
        
        if not connection_status:
            return DatabaseMetrics(
                db_type=self.db_type.value,
                timestamp=datetime.utcnow().isoformat(),
                total_size_mb=0.0,
                table_count=0,
                connection_status=False,
                health_score=0.0,
                warnings=["Database connection failed"],
                table_stats=[]
            )
        
        # Get metrics
        db_size = self.get_database_size()
        table_count = self.get_table_count()
        table_stats = self.get_table_statistics()
        
        # Check for warnings
        if db_size > 1000:  # More than 1GB
            warnings.append(f"Database size is large: {db_size:.2f} MB")
            health_score -= 10
            
        if table_count == 0:
            warnings.append("No tables found in database")
            health_score -= 20
            
        if table_count > 100:
            warnings.append(f"High number of tables: {table_count}")
            health_score -= 5
        
        # Check for tables with excessive rows
        for table in table_stats:
            if table['row_count'] > 1000000:  # More than 1M rows
                warnings.append(f"Table '{table['table_name']}' has {table['row_count']:,} rows")
                health_score -= 5
        
        # Ensure health score is between 0 and 100
        health_score = max(0, min(100, health_score))
        
        metrics = DatabaseMetrics(
            db_type=self.db_type.value,
            timestamp=datetime.utcnow().isoformat(),
            total_size_mb=db_size,
            table_count=table_count,
            connection_status=connection_status,
            health_score=health_score,
            warnings=warnings,
            table_stats=table_stats
        )
        
        # Store in history
        self.health_history.append(metrics)
        
        self.disconnect()
        return metrics
    
    def generate_report(self, metrics: DatabaseMetrics) -> str:
        """
        Generate a formatted health report
        
        Args:
            metrics: DatabaseMetrics object
            
        Returns:
            str: Formatted report
        """
        report = []
        report.append("=" * 60)
        report.append("DATABASE HEALTH REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {metrics.timestamp}")
        report.append(f"Database Type: {metrics.db_type.upper()}")
        report.append("")
        
        report.append("BASIC METRICS:")
        report.append(f"  Connection Status: {'✓ Connected' if metrics.connection_status else '✗ Disconnected'}")
        report.append(f"  Health Score: {metrics.health_score:.1f}/100.0")
        report.append(f"  Total Size: {metrics.total_size_mb:.2f} MB")
        report.append(f"  Table Count: {metrics.table_count}")
        report.append("")
        
        if metrics.warnings:
            report.append("WARNINGS:")
            for warning in metrics.warnings:
                report.append(f"  ⚠ {warning}")
            report.append("")
        
        if metrics.table_stats:
            report.append("TABLE STATISTICS:")
            report.append("-" * 60)
            report.append(f"{'Table Name':<25} {'Rows':>12} {'Columns':>8} {'Size (MB)':>10}")
            report.append("-" * 60)
            
            for table in metrics.table_stats:
                report.append(
                    f"{table['table_name']:<25} "
                    f"{table['row_count']:>12,} "
                    f"{table['column_count']:>8} "
                    f"{table['size_estimate_mb']:>10.2f}"
                )
            report.append("-" * 60)
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_metrics_json(self, metrics: DatabaseMetrics, filepath: str) -> bool:
        """
        Export metrics to JSON file
        
        Args:
            metrics: DatabaseMetrics object
            filepath: Output file path
            
        Returns:
            bool: True if successful
        """
        try:
            data = {
                'timestamp': metrics.timestamp,
                'db_type': metrics.db_type,
                'total_size_mb': metrics.total_size_mb,
                'table_count': metrics.table_count,
                'connection_status': metrics.connection_status,
                'health_score': metrics.health_score,
                'warnings': metrics.warnings,
                'table_stats': metrics.table_stats
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting metrics: {str(e)}")
            return False


def create_sample_sqlite_db(db_path: str = 'bot.db') -> None:
    """Create a sample SQLite database for testing"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create sample tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_logs (
                id INTEGER PRIMARY KEY,
                level TEXT,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Sample database created: {db_path}")
        
    except Exception as e:
        logger.error(f"Error creating sample database: {str(e)}")


def main():
    """Main execution function for testing"""
    # Configuration for SQLite (default)
    db_config = {
        'type': 'sqlite',
        'path': 'bot.db'
    }
    
    # Create sample database if it doesn't exist
    if not os.path.exists(db_config['path']):
        create_sample_sqlite_db(db_config['path'])
    
    # Initialize monitor
    monitor = DatabaseHealthMonitor(db_config)
    
    # Perform health check
    print("Performing database health check...")
    metrics = monitor.check_health()
    
    # Generate and print report
    report = monitor.generate_report(metrics)
    print(report)
    
    # Export metrics
    monitor.export_metrics_json(metrics, 'db_health_metrics.json')


if __name__ == "__main__":
    main()
