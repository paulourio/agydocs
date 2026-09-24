// Package examples provides production-grade programmatic client wrappers for the Google Cloud CLI (gcloud).
package examples

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"os/exec"
	"strings"
	"time"
)

var (
	// ErrCommandExecution indicates a non-zero exit status from gcloud.
	ErrCommandExecution = errors.New("gcloud command execution failed")
	// ErrInvalidArguments indicates missing or malformed CLI arguments.
	ErrInvalidArguments = errors.New("invalid gcloud arguments")
	// ErrTimeout indicates a context deadline cancellation.
	ErrTimeout = errors.New("gcloud command timed out")
)

// ClientOptions configures programmatic gcloud execution parameters.
type ClientOptions struct {
	BinaryPath                string
	Project                   string
	ImpersonateServiceAccount string
	Configuration             string
	DefaultTimeout            time.Duration
}

// Client wraps gcloud binary execution with structured parsing and error isolation.
type Client struct {
	opts ClientOptions
}

// NewClient creates a configured gcloud Client instance.
func NewClient(opts ClientOptions) (*Client, error) {
	if opts.BinaryPath == "" {
		opts.BinaryPath = "gcloud"
	}
	if opts.DefaultTimeout <= 0 {
		opts.DefaultTimeout = 30 * time.Second
	}
	return &Client{opts: opts}, nil
}

// ComputeInstance represents a Compute Engine virtual machine descriptor.
type ComputeInstance struct {
	ID                string             `json:"id"`
	Name              string             `json:"name"`
	Zone              string             `json:"zone"`
	Status            string             `json:"status"`
	MachineType       string             `json:"machineType"`
	CreationTimestamp string             `json:"creationTimestamp"`
	NetworkInterfaces []NetworkInterface `json:"networkInterfaces,omitempty"`
	Labels            map[string]string  `json:"labels,omitempty"`
}

// NetworkInterface models network IP attachments on an instance.
type NetworkInterface struct {
	Network       string         `json:"network"`
	NetworkIP     string         `json:"networkIP"`
	AccessConfigs []AccessConfig `json:"accessConfigs,omitempty"`
}

// AccessConfig represents external NAT IPs on a network interface.
type AccessConfig struct {
	Name  string `json:"name"`
	NatIP string `json:"natIP"`
	Type  string `json:"type"`
}

// StorageBucket represents a Cloud Storage bucket resource.
type StorageBucket struct {
	Name         string `json:"name"`
	Location     string `json:"location"`
	StorageClass string `json:"storageClass"`
	TimeCreated  string `json:"timeCreated"`
}

// CommandRunner defines the execution contract for running gcloud commands.
type CommandRunner func(ctx context.Context, name string, args ...string) ([]byte, []byte, int, error)

// DefaultCommandRunner executes binary commands via os/exec.
func DefaultCommandRunner(ctx context.Context, name string, args ...string) ([]byte, []byte, int, error) {
	cmd := exec.CommandContext(ctx, name, args...)
	cmd.Env = append(cmd.Environ(), "CLOUDSDK_CORE_DISABLE_PROMPTS=1")

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	exitCode := 0
	if err != nil {
		var exitErr *exec.ExitError
		if errors.As(err, &exitErr) {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}
	return stdout.Bytes(), stderr.Bytes(), exitCode, err
}

// BuildCommandArgs compiles base global flags alongside command-specific arguments.
func (c *Client) BuildCommandArgs(subcommandArgs []string, format string) []string {
	var args []string
	args = append(args, subcommandArgs...)

	if c.opts.Project != "" {
		args = append(args, fmt.Sprintf("--project=%s", c.opts.Project))
	}
	if c.opts.ImpersonateServiceAccount != "" {
		args = append(args, fmt.Sprintf("--impersonate-service-account=%s", c.opts.ImpersonateServiceAccount))
	}
	if c.opts.Configuration != "" {
		args = append(args, fmt.Sprintf("--configuration=%s", c.opts.Configuration))
	}

	args = append(args, "--quiet")
	if format != "" {
		args = append(args, fmt.Sprintf("--format=%s", format))
	}

	return args
}

// ExecuteRaw dispatches a gcloud command using the provided runner.
func (c *Client) ExecuteRaw(ctx context.Context, runner CommandRunner, subcommandArgs []string, format string) ([]byte, error) {
	if len(subcommandArgs) == 0 {
		return nil, fmt.Errorf("%w: subcommandArgs cannot be empty", ErrInvalidArguments)
	}

	args := c.BuildCommandArgs(subcommandArgs, format)
	stdout, stderr, exitCode, err := runner(ctx, c.opts.BinaryPath, args...)

	if ctx.Err() != nil {
		return nil, fmt.Errorf("%w: %w", ErrTimeout, ctx.Err())
	}

	if exitCode != 0 || err != nil {
		errMessage := strings.TrimSpace(string(stderr))
		if errMessage == "" {
			errMessage = err.Error()
		}
		return nil, fmt.Errorf("%w (exit %d): %s", ErrCommandExecution, exitCode, errMessage)
	}

	return stdout, nil
}

// ExecuteJSON parses JSON output from gcloud into the target destination.
func (c *Client) ExecuteJSON(ctx context.Context, runner CommandRunner, subcommandArgs []string, target any) error {
	raw, err := c.ExecuteRaw(ctx, runner, subcommandArgs, "json")
	if err != nil {
		return err
	}
	if err := json.Unmarshal(raw, target); err != nil {
		return fmt.Errorf("failed to unmarshal gcloud JSON response: %w", err)
	}
	return nil
}

// BuildFilterExpression compiles safe boolean filter predicates for gcloud.
func BuildFilterExpression(terms map[string]string) string {
	if len(terms) == 0 {
		return ""
	}
	var parts []string
	for k, v := range terms {
		if strings.Contains(v, "*") {
			parts = append(parts, fmt.Sprintf("%s:%s", k, v))
		} else {
			parts = append(parts, fmt.Sprintf("%s=%s", k, v))
		}
	}
	return strings.Join(parts, " AND ")
}
