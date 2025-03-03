import { ShapeStream, Shape } from '@electric-sql/client';
import type { ShapeData } from '@electric-sql/client';
import type { Feature, FeatureCollection } from 'geojson';
import type { LngLatLike } from 'svelte-maplibre';

const API_URL = import.meta.env.VITE_API_URL;

type entitiesStatusListType = {
	osmid: number | undefined;
	entity_id: string;
	project_id: number;
	status: 'READY' | 'OPENED_IN_ODK' | 'SURVEY_SUBMITTED' | 'MARKED_BAD' | 'VALIDATED';
	task_id: number;
};

type entitiesListType = {
	id: string;
	task_id: number;
	osm_id: number;
	status: number;
	updated_at: string | null;
};

type entitiesShapeType = {
	entity_id: string;
	status: string;
	project_id: number;
	task_id: number;
};

type entityIdCoordinateMapType = {
	entityId: string;
	coordinate: [number, number];
};

type newBadGeomType<T> = {
	geojson: Feature;
	id: number;
	project_id: number;
	status: T;
	task_id: number;
};

let userLocationCoord: LngLatLike | undefined = $state();
let selectedEntity: string | null = $state(null);
let entitiesShape: Shape;
let geomShape: Shape;
let entitiesStatusList: entitiesStatusListType[] = $state([]);
let badGeomList: FeatureCollection = $state({ type: 'FeatureCollection', features: [] });
let newGeomList: FeatureCollection = $state({ type: 'FeatureCollection', features: [] });
let syncEntityStatusLoading: boolean = $state(false);
let updateEntityStatusLoading: boolean = $state(false);
let selectedEntityCoordinate: entityIdCoordinateMapType | null = $state(null);
let entityToNavigate: entityIdCoordinateMapType | null = $state(null);
let toggleGeolocation: boolean = $state(false);

function getEntityStatusStream(projectId: number): ShapeStream | undefined {
	if (!projectId) {
		return;
	}
	return new ShapeStream({
		url: `${import.meta.env.VITE_SYNC_URL}/v1/shape`,
		table: 'odk_entities',
		where: `project_id=${projectId}`,
	});
}

function getNewBadGeomStream(projectId: number): ShapeStream | undefined {
	if (!projectId) {
		return;
	}
	return new ShapeStream({
		url: `${import.meta.env.VITE_SYNC_URL}/v1/shape`,
		table: 'geometrylog',
		where: `project_id=${projectId}`,
	});
}

function getEntitiesStatusStore() {
	async function subscribeToEntityStatusUpdates(
		entitiesStream: ShapeStream | undefined,
		entitiesList: entitiesListType[],
	) {
		if (!entitiesStream) return;
		entitiesShape = new Shape(entitiesStream);

		entitiesShape.subscribe((entities: ShapeData) => {
			const rows: entitiesShapeType[] = entities.rows;
			if (rows && Array.isArray(rows)) {
				entitiesStatusList = rows?.map((entity) => {
					return {
						...entity,
						osmid: entitiesList?.find((entityx) => entityx.id === entity.entity_id)?.osm_id,
					};
				});
			}
		});
	}

	async function subscribeToNewBadGeom(geomStream: ShapeStream | undefined) {
		if (!geomStream) return;
		geomShape = new Shape(geomStream);

		geomShape.subscribe((geom: ShapeData) => {
			const rows: newBadGeomType<'NEW' | 'BAD'>[] = geom.rows;
			const badRows = rows.filter((row) => row.status === 'BAD').map((row) => row?.geojson) as Feature[];
			const newRows = rows.filter((row) => row.status === 'NEW').map((row) => row?.geojson) as Feature[];

			if (rows && Array.isArray(rows)) {
				badGeomList = {
					type: 'FeatureCollection',
					features: badRows,
				};
				newGeomList = {
					type: 'FeatureCollection',
					features: newRows,
				};
			}
		});
	}

	async function setSelectedEntity(entityOsmId: number | null) {
		selectedEntity = entityOsmId;
	}

	async function setSelectedEntityCoordinate(entityCoordinate: entityIdCoordinateMapType | null) {
		selectedEntityCoordinate = entityCoordinate;
	}

	async function syncEntityStatus(projectId: number) {
		try {
			syncEntityStatusLoading = true;
			await fetch(`${API_URL}/projects/${projectId}/entities/statuses`, {
				credentials: 'include',
			});
			syncEntityStatusLoading = false;
		} catch (error) {
			syncEntityStatusLoading = false;
		}
	}

	async function updateEntityStatus(projectId: number, payload: Record<string, any>) {
		try {
			updateEntityStatusLoading = true;
			await fetch(`${import.meta.env.VITE_API_URL}/projects/${projectId}/entity/status`, {
				method: 'POST',
				body: JSON.stringify(payload),
				headers: {
					'Content-type': 'application/json',
				},
				credentials: 'include',
			});
			updateEntityStatusLoading = false;
		} catch (error) {
			updateEntityStatusLoading = false;
		}
	}

	function setEntityToNavigate(entityCoordinate: entityIdCoordinateMapType | null) {
		entityToNavigate = entityCoordinate;
	}

	function setToggleGeolocation(status: boolean) {
		toggleGeolocation = status;
	}

	function setUserLocationCoordinate(coordinate: LngLatLike | undefined) {
		userLocationCoord = coordinate;
	}

	return {
		subscribeToEntityStatusUpdates: subscribeToEntityStatusUpdates,
		setSelectedEntity: setSelectedEntity,
		syncEntityStatus: syncEntityStatus,
		updateEntityStatus: updateEntityStatus,
		setSelectedEntityCoordinate: setSelectedEntityCoordinate,
		setEntityToNavigate: setEntityToNavigate,
		setToggleGeolocation: setToggleGeolocation,
		setUserLocationCoordinate: setUserLocationCoordinate,
		subscribeToNewBadGeom: subscribeToNewBadGeom,
		get selectedEntity() {
			return selectedEntity;
		},
		get entitiesStatusList() {
			return entitiesStatusList;
		},
		get badGeomList() {
			return badGeomList;
		},
		get newGeomList() {
			return newGeomList;
		},
		get syncEntityStatusLoading() {
			return syncEntityStatusLoading;
		},
		get updateEntityStatusLoading() {
			return updateEntityStatusLoading;
		},
		get selectedEntityCoordinate() {
			return selectedEntityCoordinate;
		},
		get entityToNavigate() {
			return entityToNavigate;
		},
		get toggleGeolocation() {
			return toggleGeolocation;
		},
		get userLocationCoord() {
			return userLocationCoord;
		},
	};
}

export { getEntityStatusStream, getEntitiesStatusStore, getNewBadGeomStream };
