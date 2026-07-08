import { Dashboard } from "@/components/Dashboard";
import type { DemoBundle } from "@/lib/types";
import bundle from "@/public/demo-data.json";

const data = bundle as unknown as DemoBundle;

export default function Home() {
  return (
    <Dashboard
      initial={data.anomalies}
      apiUrl={process.env.NEXT_PUBLIC_API_URL}
      generatedWith={data.generated_with}
    />
  );
}
