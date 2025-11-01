# GCP GPU Options for LangChain Research Agent

## GPU Comparison for Local LLM Inference

### Recommended GPUs (Cost-Effective Options)

| GPU Type | VRAM | Cost/Hour | Cost/Month* | Best For | Availability |
|----------|------|-----------|-------------|----------|--------------|
| **nvidia-tesla-p4** | 8GB | ~$0.30-0.35 | ~$220-250 | Llama 2 7B Q4 | ✅ Good in Europe |
| **nvidia-tesla-t4** | 16GB | ~$0.35-0.40 | ~$250-290 | Llama 2 7B-13B | ⚠️ High demand |
| **nvidia-l4** | 24GB | ~$0.60-0.65 | ~$430-470 | Llama 2 70B (Q2) | ✅ Good availability |
| **nvidia-tesla-p100** | 16GB | ~$1.46 | ~$1,050 | Older, not recommended | Limited |
| **nvidia-tesla-v100** | 16GB | ~$2.48 | ~$1,785 | High performance | Limited |

*Costs assume 24/7 usage. Actual costs will vary based on usage.

### Model Recommendations by GPU

#### P4 (8GB VRAM) - CHEAPEST OPTION ✅
- **Llama 2 7B Q4_K_M**: ~4-5GB VRAM usage
- **Llama 2 7B Q3_K_S**: ~3-4GB VRAM usage
- **Phi-2**: ~2-3GB VRAM usage
- **Smaller models**: Orca Mini, etc.

#### T4 (16GB VRAM) - RECOMMENDED
- **Llama 2 7B Q4_K_M**: ~4-5GB VRAM usage
- **Llama 2 13B Q4_K_M**: ~7-8GB VRAM usage
- **Llama 2 70B Q2_K**: ~14-15GB VRAM usage

#### L4 (24GB VRAM)
- All T4 models plus:
- **Llama 2 70B Q3_K_M**: ~20-22GB VRAM usage
- **Llama 2 70B Q4_K_M**: ~22-24GB VRAM usage

## Current Instance Status

**Active Instance:**
- **GPU:** nvidia-tesla-p4
- **Zone:** europe-west4-b (Eemshaven, Netherlands)
- **Instance:** langchain-gpu-instance
- **IP:** 34.34.27.155
- **Status:** RUNNING

## Why P4?

1. **Cheapest option** (~$220-250/month vs $250-290 for T4)
2. **Good availability** in European regions
3. **Sufficient for 7B models** - Llama 2 7B Q4_K_M fits comfortably in 8GB
4. **Optimized for inference** - P4 is specifically designed for inference workloads

## Availability by Region

### European Regions (Good P4 Availability)
- ✅ **europe-west4-b, -c** (Netherlands) - P4 available
- ✅ **europe-west1-b, -c, -d** (Belgium) - T4 available
- ✅ **europe-west2, -3** - Various GPUs

### US Regions
- ⚠️ **us-central1** - High demand, often exhausted
- ⚠️ **us-east1, us-west1** - Moderate availability

## Cost Optimization Tips

1. **Use Preemptible Instances**: Save up to 80% (but can be terminated)
2. **Stop when not in use**: Only pay for compute time when instance is running
3. **Use smaller quantized models**: Q4_K_M instead of Q5 gives 95% quality with 20% less VRAM
4. **Consider Cloud Run GPUs**: Pay-per-second, scale to zero (if compatible with your workload)

## Switching GPUs

If you want to switch to a T4 later (when available), you'll need to:
1. Stop and delete current instance
2. Create new instance with T4 GPU
3. Reinstall and configure

Or create a snapshot/disk image to reuse your setup.

## References

- [GCP GPU Pricing](https://cloud.google.com/compute/docs/gpus/pricing)
- [GCP GPU Regions and Zones](https://cloud.google.com/compute/docs/gpus/gpu-regions-zones)
- [Llama 2 Model Sizes](https://huggingface.co/models?search=llama-2)

