import type {ReactNode} from 'react';
import clsx from 'clsx';
import Link from '@docusaurus/Link';
import useDocusaurusContext from '@docusaurus/useDocusaurusContext';
import Layout from '@theme/Layout';
import Heading from '@theme/Heading';

import styles from './index.module.css';

const phases = [
  {title: 'Phase 1: Foundation', months: '1-3', services: 16, desc: 'API Gateway, Auth, Users, Admin Dashboard'},
  {title: 'Phase 2: Events', months: '4-6', services: 49, desc: 'Drivers, Trips, Dispatch, Pricing, Payments'},
  {title: 'Phase 3: Data Platform', months: '7-9', services: 27, desc: 'Streaming, ClickHouse, Data Lake, ETL'},
  {title: 'Phase 4: ML Platform', months: '10-12', services: 19, desc: 'Feature Store, Training, Serving, Monitoring'},
  {title: 'Phase 5: DevOps', months: '13-16', services: 10, desc: 'Kubernetes, CI/CD, Observability, SLOs'},
  {title: 'Phase 6: Advanced AI', months: '17-20', services: 15, desc: 'ETA, Fraud, NLP, RL Dispatch'},
  {title: 'Phase 7: Global Scale', months: '21-24', services: 19, desc: 'Multi-Region, Chaos, Performance, Capstone'},
];

function HomepageHeader() {
  const {siteConfig} = useDocusaurusContext();
  return (
    <header className={clsx('hero hero--primary', styles.heroBanner)}>
      <div className="container">
        <Heading as="h1" className="hero__title">
          {siteConfig.title}
        </Heading>
        <p className="hero__subtitle">{siteConfig.tagline}</p>
        <div className={styles.buttons}>
          <Link
            className="button button--secondary button--lg"
            to="/docs/intro">
            Start Learning Path
          </Link>
        </div>
      </div>
    </header>
  );
}

function PhaseCard({title, months, services, desc}: {title: string; months: string; services: number; desc: string}) {
  return (
    <div className={clsx('col col--4', styles.phaseCard)}>
      <div className="card shadow--md" style={{height: '100%'}}>
        <div className="card__header">
          <Heading as="h3">{title}</Heading>
        </div>
        <div className="card__body">
          <p>{desc}</p>
          <small>Months {months} &middot; {services} services</small>
        </div>
      </div>
    </div>
  );
}

export default function Home(): ReactNode {
  return (
    <Layout
      title="Home"
      description="Enterprise-grade ride-hailing platform — 2-year learning curriculum covering 155 microservices, ML, AI, and data at scale">
      <HomepageHeader />
      <main>
        <section style={{padding: '2rem 0'}}>
          <div className="container">
            <div className="row" style={{gap: '1rem 0'}}>
              {phases.map((phase) => (
                <PhaseCard key={phase.title} {...phase} />
              ))}
            </div>
          </div>
        </section>
        <section style={{padding: '2rem 0', background: 'var(--ifm-background-surface-color)'}}>
          <div className="container" style={{textAlign: 'center'}}>
            <Heading as="h2">Built with Real Data</Heading>
            <p>
              1.7B+ NYC taxi trips &middot; 155 microservices &middot; 42 learning modules &middot; 6 databases
            </p>
          </div>
        </section>
      </main>
    </Layout>
  );
}
