// Keep this project server focused: its main graph on startup and only project nodes in the library.
import { app } from '../../scripts/app.js';
import { api } from '../../scripts/api.js';

app.registerExtension({
  name: 'yesopen.projectWorkspace',
  async init() {
    try {
      const response = await api.fetchApi('/yesopen/project-profile');
      if (!response.ok) throw new Error(`Project profile: HTTP ${response.status}`);
      const profile = await response.json();
      const allowed = new Set(profile.node_types);
      const getNodeDefs = api.getNodeDefs.bind(api);
      api.getNodeDefs = async (...args) => {
        const defs = await getNodeDefs(...args);
        return Object.fromEntries(Object.entries(defs).filter(([name]) => allowed.has(name)));
      };

      // Startup restoration calls loadGraphData after extension initialization.
      // An explicitly linked project template still opens as requested.
      const useDefault = !location.hash || location.hash === '#yesopen-skit-pipeline';
      const loadGraphData = app.loadGraphData.bind(app);
      let firstLoad = true;
      app.loadGraphData = async (...args) => {
        if (firstLoad && useDefault) {
          firstLoad = false;
          try {
            const response = await api.getUserData(profile.workflow);
            if (!response.ok) throw new Error(`Default workflow: HTTP ${response.status}`);
            const graph = await response.json();
            return await loadGraphData(graph, true, true, profile.workflow);
          } catch (error) {
            console.error('[yesopen.projectWorkspace] Default graph could not be loaded', error);
            return loadGraphData(...args);
          }
        }
        firstLoad = false;
        return loadGraphData(...args);
      };
    } catch (error) {
      console.error('[yesopen.projectWorkspace]', error);
    }
  },
});
