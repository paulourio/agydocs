package examples

import (
	"context"
	"errors"
	"strings"
	"testing"
)

func TestBuildCommandArgs(t *testing.T) {
	client, err := NewClient(ClientOptions{
		BinaryPath:                "/usr/bin/gcloud",
		Project:                   "test-proj-123",
		ImpersonateServiceAccount: "test-sa@test-proj-123.iam.gserviceaccount.com",
		Configuration:             "test-config",
	})
	if err != nil {
		t.Fatalf("unexpected NewClient error: %v", err)
	}

	args := client.BuildCommandArgs([]string{"compute", "instances", "list"}, "json")

	expectedFlags := []string{
		"compute",
		"instances",
		"list",
		"--project=test-proj-123",
		"--impersonate-service-account=test-sa@test-proj-123.iam.gserviceaccount.com",
		"--configuration=test-config",
		"--quiet",
		"--format=json",
	}

	if len(args) != len(expectedFlags) {
		t.Fatalf("expected %d args, got %d: %v", len(expectedFlags), len(args), args)
	}

	for i, exp := range expectedFlags {
		if args[i] != exp {
			t.Errorf("arg[%d] expected '%s', got '%s'", i, exp, args[i])
		}
	}
}

func TestBuildFilterExpression(t *testing.T) {
	terms := map[string]string{
		"status": "RUNNING",
	}
	expr := BuildFilterExpression(terms)
	if expr != "status=RUNNING" {
		t.Errorf("expected 'status=RUNNING', got '%s'", expr)
	}

	wildcardTerms := map[string]string{
		"zone": "us-central1-*",
	}
	wExpr := BuildFilterExpression(wildcardTerms)
	if wExpr != "zone:us-central1-*" {
		t.Errorf("expected 'zone:us-central1-*', got '%s'", wExpr)
	}
}

func TestExecuteJSONSuccess(t *testing.T) {
	client, err := NewClient(ClientOptions{})
	if err != nil {
		t.Fatalf("NewClient error: %v", err)
	}

	mockRunner := func(ctx context.Context, name string, args ...string) ([]byte, []byte, int, error) {
		payload := `[
			{
				"id": "1001",
				"name": "worker-01",
				"zone": "us-central1-a",
				"status": "RUNNING",
				"machineType": "e2-medium",
				"creationTimestamp": "2026-03-24T10:00:00Z",
				"networkInterfaces": [
					{
						"network": "core-vpc",
						"networkIP": "10.10.0.5",
						"accessConfigs": [
							{"name": "external-nat", "natIP": "35.200.10.20", "type": "ONE_TO_ONE_NAT"}
						]
					}
				]
			}
		]`
		return []byte(payload), nil, 0, nil
	}

	var instances []ComputeInstance
	err = client.ExecuteJSON(context.Background(), mockRunner, []string{"compute", "instances", "list"}, &instances)
	if err != nil {
		t.Fatalf("ExecuteJSON unexpected error: %v", err)
	}

	if len(instances) != 1 {
		t.Fatalf("expected 1 instance, got %d", len(instances))
	}
	inst := instances[0]
	if inst.Name != "worker-01" || inst.Status != "RUNNING" {
		t.Errorf("unexpected instance data: %+v", inst)
	}
	if len(inst.NetworkInterfaces) != 1 || inst.NetworkInterfaces[0].NetworkIP != "10.10.0.5" {
		t.Errorf("unexpected network interface: %+v", inst.NetworkInterfaces)
	}
}

func TestExecuteErrorHandling(t *testing.T) {
	client, err := NewClient(ClientOptions{})
	if err != nil {
		t.Fatalf("NewClient error: %v", err)
	}

	mockRunner := func(ctx context.Context, name string, args ...string) ([]byte, []byte, int, error) {
		return nil, []byte("ERROR: (gcloud.compute.instances.create) Quota 'CPUS' exceeded. Limit: 24.0"), 1, errors.New("exit status 1")
	}

	var instances []ComputeInstance
	err = client.ExecuteJSON(context.Background(), mockRunner, []string{"compute", "instances", "create", "test-vm"}, &instances)
	if err == nil {
		t.Fatal("expected error on non-zero exit code, got nil")
	}

	if !errors.Is(err, ErrCommandExecution) {
		t.Errorf("expected ErrCommandExecution, got %v", err)
	}
	if !strings.Contains(err.Error(), "Quota 'CPUS' exceeded") {
		t.Errorf("expected error message to contain quota details, got '%v'", err)
	}
}

func TestExecuteContextCancellation(t *testing.T) {
	client, err := NewClient(ClientOptions{})
	if err != nil {
		t.Fatalf("NewClient error: %v", err)
	}

	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancel immediately

	mockRunner := func(ctx context.Context, name string, args ...string) ([]byte, []byte, int, error) {
		return nil, nil, 0, ctx.Err()
	}

	var instances []ComputeInstance
	err = client.ExecuteJSON(ctx, mockRunner, []string{"compute", "instances", "list"}, &instances)
	if err == nil {
		t.Fatal("expected timeout error, got nil")
	}

	if !errors.Is(err, ErrTimeout) {
		t.Errorf("expected ErrTimeout, got %v", err)
	}
}
