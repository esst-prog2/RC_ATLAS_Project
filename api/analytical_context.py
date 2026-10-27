"""Strict, optional calculation context for existing read endpoints."""
from typing import Optional
from fastapi import Request, HTTPException
from services.analytical_consumers import selection
from services.errors import ServiceError


def analytical_query(request: Request, start: Optional[str] = None, end: Optional[str] = None,
                     as_of: Optional[str] = None, methodology_id: str = '', version: str = '',
                     locale: str = 'EN', project_id: str = '', indicator_id: str = ''):
    allowed = {'start', 'end', 'as_of', 'methodology_id', 'version', 'locale', 'project_id', 'indicator_id'}
    if set(request.query_params) - allowed or any(len(request.query_params.getlist(k)) != 1 for k in request.query_params):
        raise HTTPException(400, 'Unsupported or repeated analytical parameters. No filter was applied.')
    path_project = request.path_params.get('project_id')
    supplied_project = request.query_params.get('project_id', '')
    if path_project and supplied_project and supplied_project != path_project:
        raise HTTPException(400, 'Project context does not match the requested resource.')
    project_id = path_project or project_id
    path_indicator = request.path_params.get('indicator_id')
    supplied_indicator = request.query_params.get('indicator_id', '')
    if path_indicator and supplied_indicator and supplied_indicator != path_indicator:
        raise HTTPException(400, 'Indicator context does not match the requested resource.')
    indicator_id = path_indicator or indicator_id
    try:
        selected = selection(start, end, as_of, methodology_id, version, locale)
    except ServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    if selected is not None and (not project_id or not indicator_id):
        raise HTTPException(400, 'Select an explicit project and indicator for calculation.')
    return {'selected': selected, 'project_id': project_id, 'indicator_id': indicator_id}
