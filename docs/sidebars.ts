import type {SidebarsConfig} from '@docusaurus/plugin-content-docs';

const sidebars: SidebarsConfig = {
  learningSidebar: [
    'intro',
    {
      type: 'category',
      label: 'Phase 1: Foundation',
      link: {type: 'doc', id: 'phase-1/index'},
      items: [
        'phase-1/getting-started',
        'phase-1/m01-api-gateway',
        'phase-1/m02-authentication',
        'phase-1/m03-rest-api-design',
        'phase-1/m04-database-patterns',
        'phase-1/m05-caching',
        'phase-1/m06-containerization',
      ],
    },
    {
      type: 'category',
      label: 'Phase 2: Events',
      link: {type: 'doc', id: 'phase-2/index'},
      items: [
        'phase-2/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Phase 3: Data Platform',
      link: {type: 'doc', id: 'phase-3/index'},
      items: [
        'phase-3/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Phase 4: ML Platform',
      link: {type: 'doc', id: 'phase-4/index'},
      items: [
        'phase-4/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Phase 5: DevOps',
      link: {type: 'doc', id: 'phase-5/index'},
      items: [
        'phase-5/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Phase 6: Advanced AI',
      link: {type: 'doc', id: 'phase-6/index'},
      items: [
        'phase-6/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Phase 7: Global Scale',
      link: {type: 'doc', id: 'phase-7/index'},
      items: [
        'phase-7/getting-started',
      ],
    },
    {
      type: 'category',
      label: 'Architecture',
      link: {type: 'doc', id: 'architecture/index'},
      items: [
        'architecture/system-overview',
        'architecture/data-strategy',
      ],
    },
  ],
};

export default sidebars;
