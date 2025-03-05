import type { Geometry as GeoJSONGeometry } from 'geojson';

import { getAlertStore } from '$store/common.svelte.ts';
import { geojsonGeomToJavarosa } from '$lib/odk/javarosa';

const alertStore = getAlertStore();

export function openOdkCollectNewFeature(xFormId: string, entityId: string) {
	if (!xFormId || !entityId) {
		return;
	}

	const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

	if (isMobile) {
		// TODO we need to update the form to support task_id=${}&
		document.location.href = `odkcollect://form/${xFormId}?feature=${entityId}`;
	} else {
		alertStore.setAlert({
			variant: 'warning',
			message: 'Requires a mobile phone with ODK Collect.',
		});
	}
}
