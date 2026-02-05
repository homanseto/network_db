from sqlalchemy import text

def validate_staging(session):
    result = session.execute(
        text("SELECT validate_network_staging();")
    )
    return result.scalar()


def get_validation_errors(session):
    result = session.execute(
        text("SELECT * FROM network_staging_errors;")
    )
    return [dict(row) for row in result.mappings()]
