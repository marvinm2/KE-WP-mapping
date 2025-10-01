#!/usr/bin/env python3
"""
Performance test for WikiPathways xref API calls.
Compares individual xref calls vs batch xrefs API for gene mapping.
"""
import time
import requests
import concurrent.futures
from typing import List, Dict, Any

# Test data - 100 sample gene identifiers
TEST_GENES = [
    "ENSG00000139618",  # BRCA2
    "ENSG00000012048",  # BRCA1
    "ENSG00000141510",  # TP53
    "ENSG00000134086",  # VHL
    "ENSG00000003056",  # M6PR
    "ENSG00000005339",  # CREBBP
    "ENSG00000006451",  # RXRA
    "ENSG00000007968",  # E2F2
    "ENSG00000008513",  # ST8SIA2
    "ENSG00000009307",  # CSRP3
    "ENSG00000000003",  # TSPAN6
    "ENSG00000000005",  # TNMD
    "ENSG00000000419",  # DPM1
    "ENSG00000000457",  # SCYL3
    "ENSG00000000460",  # C1orf112
    "ENSG00000000938",  # FGR
    "ENSG00000000971",  # CFH
    "ENSG00000001036",  # FUCA2
    "ENSG00000001084",  # GCLC
    "ENSG00000001167",  # NFYA
    "ENSG00000001460",  # STPG1
    "ENSG00000001461",  # NIPAL3
    "ENSG00000001497",  # LAS1L
    "ENSG00000001561",  # ENPP4
    "ENSG00000001617",  # SEMA3F
    "ENSG00000001626",  # CFTR
    "ENSG00000001629",  # ANKIB1
    "ENSG00000001630",  # CYP51A1
    "ENSG00000001631",  # KRIT1
    "ENSG00000002016",  # RAD52
    "ENSG00000002079",  # MYH16
    "ENSG00000002330",  # BAD
    "ENSG00000002549",  # LAP3
    "ENSG00000002586",  # CD99
    "ENSG00000002587",  # HS3ST1
    "ENSG00000002822",  # MAD1L1
    "ENSG00000002834",  # LASP1
    "ENSG00000003056",  # M6PR
    "ENSG00000003096",  # KLHL13
    "ENSG00000003137",  # CYP26B1
    "ENSG00000003249",  # DBNDD1
    "ENSG00000003393",  # ALS2
    "ENSG00000003400",  # CASP10
    "ENSG00000003402",  # CFLAR
    "ENSG00000003436",  # TFPI
    "ENSG00000003509",  # NDUFAB1
    "ENSG00000003756",  # RBM15
    "ENSG00000003987",  # MTND1P23
    "ENSG00000003989",  # SLC7A2
    "ENSG00000004059",  # ARF5
    "ENSG00000004139",  # KDM1A
    "ENSG00000004142",  # POLDIP2
    "ENSG00000004399",  # PTPN22
    "ENSG00000004455",  # AK2
    "ENSG00000004468",  # CD38
    "ENSG00000004478",  # FKBP4
    "ENSG00000004487",  # KDM1B
    "ENSG00000004534",  # RBM6
    "ENSG00000004576",  # UCHL5
    "ENSG00000004700",  # RECQL
    "ENSG00000004766",  # VDAC1
    "ENSG00000004777",  # ARHGAP33
    "ENSG00000004779",  # NDUFAB1
    "ENSG00000004799",  # PDK4
    "ENSG00000004838",  # ARMCX1
    "ENSG00000004848",  # ARX
    "ENSG00000004864",  # SLC25A6
    "ENSG00000004897",  # CDC27
    "ENSG00000004961",  # HYPK
    "ENSG00000005007",  # UPF1
    "ENSG00000005020",  # SKAP2
    "ENSG00000005022",  # SLC25A5
    "ENSG00000005059",  # MCMDC2
    "ENSG00000005073",  # HOXA11
    "ENSG00000005075",  # POLR2J
    "ENSG00000005100",  # DHX57
    "ENSG00000005102",  # BIRC3
    "ENSG00000005108",  # THSD7A
    "ENSG00000005156",  # LIG3
    "ENSG00000005175",  # RPAP3
    "ENSG00000005189",  # AC104389.8
    "ENSG00000005194",  # CIAPIN1
    "ENSG00000005206",  # SPPL3
    "ENSG00000005243",  # COPB2
    "ENSG00000005249",  # PRKAR2A
    "ENSG00000005339",  # CREBBP
    "ENSG00000005381",  # MPO
    "ENSG00000005421",  # ITGA2
    "ENSG00000005448",  # WDR18
    "ENSG00000005469",  # CROT
    "ENSG00000005471",  # ABCF2
    "ENSG00000005483",  # KMT2A
    "ENSG00000005486",  # RHBDD2
    "ENSG00000005513",  # RHOA
    "ENSG00000005520",  # PSAP
    "ENSG00000005531",  # DMC1
    "ENSG00000005534",  # PMS1
    "ENSG00000005566",  # ARPC2
    "ENSG00000005567",  # ARPC1B
    "ENSG00000005596",  # CENPF
    "ENSG00000005700",  # TLE3
    "ENSG00000005801",  # ZNF131
    "ENSG00000005812",  # CAMP
]

BASE_URL = "https://webservice.bridgedb.org"

def test_individual_xref_calls(genes: List[str], system_code: str = "En") -> Dict[str, Any]:
    """Test individual xref API calls."""
    print(f"\n=== Testing Individual xref Calls ===")
    print(f"Testing {len(genes)} genes with system code: {system_code}")
    
    start_time = time.time()
    results = []
    successful_calls = 0
    failed_calls = 0
    
    for gene in genes:
        try:
            gene_start = time.time()
            url = f"{BASE_URL}/Human/xrefs/{system_code}/{gene}"
            response = requests.get(url, timeout=10)
            gene_time = time.time() - gene_start
            
            if response.status_code == 200:
                successful_calls += 1
                xrefs = response.text.strip().split('\n') if response.text.strip() else []
                results.append({
                    'gene': gene,
                    'xrefs_count': len(xrefs),
                    'response_time': gene_time,
                    'status': 'success'
                })
                print(f"  {gene}: {len(xrefs)} xrefs in {gene_time:.3f}s")
            else:
                failed_calls += 1
                results.append({
                    'gene': gene,
                    'xrefs_count': 0,
                    'response_time': gene_time,
                    'status': f'failed_{response.status_code}'
                })
                print(f"  {gene}: FAILED ({response.status_code}) in {gene_time:.3f}s")
                
        except Exception as e:
            failed_calls += 1
            results.append({
                'gene': gene,
                'xrefs_count': 0,
                'response_time': 0,
                'status': f'error_{str(e)[:50]}'
            })
            print(f"  {gene}: ERROR - {str(e)[:50]}")
    
    total_time = time.time() - start_time
    avg_time_per_gene = total_time / len(genes)
    
    return {
        'method': 'individual',
        'total_time': total_time,
        'avg_time_per_gene': avg_time_per_gene,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'results': results
    }

def test_batch_xrefs_call(genes: List[str], system_code: str = "En") -> Dict[str, Any]:
    """Test batch xrefs API call."""
    print(f"\n=== Testing Batch xrefs Call ===")
    print(f"Testing {len(genes)} genes with system code: {system_code}")
    
    start_time = time.time()
    
    try:
        # Prepare batch request body - just gene identifiers, one per line
        batch_data = '\n'.join(genes)
        
        url = f"{BASE_URL}/Human/xrefsBatch/{system_code}"
        headers = {'Content-Type': 'text/plain'}
        
        response = requests.post(url, data=batch_data, headers=headers, timeout=30)
        total_time = time.time() - start_time
        
        if response.status_code == 200:
            # Parse batch response - each line has format: gene_id\tsystem\txref1,xref2,xref3...
            lines = response.text.strip().split('\n')
            gene_results = {}
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 3:
                        source_id = parts[0]
                        system_code = parts[1]
                        xrefs_str = parts[2]
                        # Count comma-separated xrefs
                        xrefs = xrefs_str.split(',') if xrefs_str else []
                        gene_results[source_id] = xrefs
            
            results = []
            for gene in genes:
                xref_count = len(gene_results.get(gene, []))
                results.append({
                    'gene': gene,
                    'xrefs_count': xref_count,
                    'response_time': total_time / len(genes),  # Distributed time
                    'status': 'success'
                })
                print(f"  {gene}: {xref_count} xrefs")
            
            return {
                'method': 'batch',
                'total_time': total_time,
                'avg_time_per_gene': total_time / len(genes),
                'successful_calls': len(genes),
                'failed_calls': 0,
                'results': results
            }
        else:
            print(f"Batch call failed with status: {response.status_code}")
            return {
                'method': 'batch',
                'total_time': total_time,
                'avg_time_per_gene': total_time / len(genes),
                'successful_calls': 0,
                'failed_calls': len(genes),
                'results': []
            }
            
    except Exception as e:
        total_time = time.time() - start_time
        print(f"Batch call error: {str(e)}")
        return {
            'method': 'batch',
            'total_time': total_time,
            'avg_time_per_gene': total_time / len(genes),
            'successful_calls': 0,
            'failed_calls': len(genes),
            'results': []
        }

def test_parallel_individual_calls(genes: List[str], system_code: str = "En", max_workers: int = 5) -> Dict[str, Any]:
    """Test individual calls with parallel processing."""
    print(f"\n=== Testing Parallel Individual Calls ===")
    print(f"Testing {len(genes)} genes with {max_workers} workers")
    
    def fetch_xref(gene: str) -> Dict[str, Any]:
        try:
            gene_start = time.time()
            url = f"{BASE_URL}/Human/xrefs/{system_code}/{gene}"
            response = requests.get(url, timeout=10)
            gene_time = time.time() - gene_start
            
            if response.status_code == 200:
                xrefs = response.text.strip().split('\n') if response.text.strip() else []
                return {
                    'gene': gene,
                    'xrefs_count': len(xrefs),
                    'response_time': gene_time,
                    'status': 'success'
                }
            else:
                return {
                    'gene': gene,
                    'xrefs_count': 0,
                    'response_time': gene_time,
                    'status': f'failed_{response.status_code}'
                }
        except Exception as e:
            return {
                'gene': gene,
                'xrefs_count': 0,
                'response_time': 0,
                'status': f'error_{str(e)[:50]}'
            }
    
    start_time = time.time()
    results = []
    successful_calls = 0
    failed_calls = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_gene = {executor.submit(fetch_xref, gene): gene for gene in genes}
        
        for future in concurrent.futures.as_completed(future_to_gene):
            result = future.result()
            results.append(result)
            
            if result['status'] == 'success':
                successful_calls += 1
                print(f"  {result['gene']}: {result['xrefs_count']} xrefs in {result['response_time']:.3f}s")
            else:
                failed_calls += 1
                print(f"  {result['gene']}: {result['status']} in {result['response_time']:.3f}s")
    
    total_time = time.time() - start_time
    avg_time_per_gene = total_time / len(genes)
    
    return {
        'method': 'parallel_individual',
        'total_time': total_time,
        'avg_time_per_gene': avg_time_per_gene,
        'successful_calls': successful_calls,
        'failed_calls': failed_calls,
        'results': results
    }

def print_performance_summary(results: List[Dict[str, Any]]):
    """Print performance comparison summary."""
    print(f"\n{'='*60}")
    print("PERFORMANCE COMPARISON SUMMARY")
    print(f"{'='*60}")
    
    for result in results:
        method = result['method']
        total_time = result['total_time']
        avg_time = result['avg_time_per_gene']
        successful = result['successful_calls']
        failed = result['failed_calls']
        
        print(f"\n{method.upper().replace('_', ' ')}:")
        print(f"  Total Time: {total_time:.3f}s")
        print(f"  Avg Time per Gene: {avg_time:.3f}s")
        print(f"  Success Rate: {successful}/{successful + failed} ({successful/(successful + failed)*100:.1f}%)")
        
        if result['results']:
            response_times = [r['response_time'] for r in result['results'] if r['response_time'] > 0]
            if response_times:
                print(f"  Min Response: {min(response_times):.3f}s")
                print(f"  Max Response: {max(response_times):.3f}s")
    
    # Find fastest method
    valid_results = [r for r in results if r['successful_calls'] > 0]
    if valid_results:
        fastest = min(valid_results, key=lambda x: x['total_time'])
        print(f"\n🏆 FASTEST METHOD: {fastest['method'].upper().replace('_', ' ')}")
        print(f"   Total time: {fastest['total_time']:.3f}s")
        
        # Calculate speedup
        slowest = max(valid_results, key=lambda x: x['total_time'])
        speedup = slowest['total_time'] / fastest['total_time']
        print(f"   Speedup: {speedup:.1f}x faster than slowest method")

def main():
    """Run performance tests."""
    print("WikiPathways xref API Performance Test")
    print(f"Testing with {len(TEST_GENES)} genes: {', '.join(TEST_GENES[:3])}...")
    
    results = []
    
    # Test 1: Individual calls
    individual_result = test_individual_xref_calls(TEST_GENES)
    results.append(individual_result)
    
    # Test 2: Batch call
    batch_result = test_batch_xrefs_call(TEST_GENES)
    results.append(batch_result)
    
    # Test 3: Parallel individual calls
    parallel_result = test_parallel_individual_calls(TEST_GENES, max_workers=5)
    results.append(parallel_result)
    
    # Print summary
    print_performance_summary(results)

if __name__ == "__main__":
    main()